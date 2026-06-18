# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Build a SUMO ``net.xml`` from a normalized VISUM SQLite network.

Writes SUMO plain XML (``*.nod.xml``, ``*.edg.xml``, ``*.typ.xml``) in already
projected cartesian coordinates, then invokes ``netconvert`` (resolved via
``sumolib.checkBinary``) without further projection, requesting ``--tls.guess``
for v1 signal control. Saves the ``.netccfg`` and the build log (osmBuild
pattern, ADR-006).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import quoteattr

from gis.normalize.visum_sqlite import (
    NetworkBuildOptions,
    NormalizedNetwork,
    VisumSQLiteError,
    normalize_sqlite_network,
)
from gis.orchestrate.subprocess_run import save_and_run

logger = logging.getLogger(__name__)


@dataclass
class NetworkBuildResult:
    net_xml_path: Optional[Path]
    netccfg_path: Optional[Path]
    log_path: Optional[Path]
    source_wkt: Optional[str]
    target_epsg: str
    node_count: int
    edge_count: int
    type_count: int
    skipped_directions: list[str] = field(default_factory=list)
    unmapped_tokens: dict[str, int] = field(default_factory=dict)
    coherence_warnings: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    netconvert_returncode: Optional[int] = None


def _fmt(value: float) -> str:
    return f"{value:.3f}"


def write_plain_xml(network: NormalizedNetwork, out_dir: Path, prefix: str = "net") -> dict[str, Path]:
    """Write SUMO plain-XML node/edge/type files; return their paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    nod_path = out_dir / f"{prefix}.nod.xml"
    edg_path = out_dir / f"{prefix}.edg.xml"
    typ_path = out_dir / f"{prefix}.typ.xml"

    nod_lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<nodes>"]
    for node in network.nodes:
        nod_lines.append(
            f'    <node id={quoteattr(node.node_id)} x="{_fmt(node.x)}" y="{_fmt(node.y)}"/>'
        )
    nod_lines.append("</nodes>")
    nod_path.write_text("\n".join(nod_lines), encoding="utf-8")

    typ_lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<types>"]
    for type_id, tdef in sorted(network.types.items()):
        if tdef.restrictions_ms:
            typ_lines.append(
                f'    <type id={quoteattr(type_id)} speed="{_fmt(tdef.speed_ms)}">'
            )
            for vclass, speed in sorted(tdef.restrictions_ms.items()):
                typ_lines.append(
                    f'        <restriction vClass={quoteattr(vclass)} speed="{_fmt(speed)}"/>'
                )
            typ_lines.append("    </type>")
        else:
            typ_lines.append(
                f'    <type id={quoteattr(type_id)} speed="{_fmt(tdef.speed_ms)}"/>'
            )
    typ_lines.append("</types>")
    typ_path.write_text("\n".join(typ_lines), encoding="utf-8")

    edg_lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<edges>"]
    for edge in network.edges:
        shape = " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in edge.shape)
        edg_lines.append(
            f'    <edge id={quoteattr(edge.edge_id)} from={quoteattr(edge.from_node)} '
            f'to={quoteattr(edge.to_node)} type={quoteattr(edge.type_id)} '
            f'numLanes="{edge.num_lanes}" speed="{_fmt(edge.speed_ms)}" '
            f'allow={quoteattr(" ".join(edge.allow))} shape={quoteattr(shape)}/>'
        )
    edg_lines.append("</edges>")
    edg_path.write_text("\n".join(edg_lines), encoding="utf-8")

    return {"nod": nod_path, "edg": edg_path, "typ": typ_path}


def build_network_from_sqlite(
    sqlite_path: str | Path,
    out_dir: str | Path,
    options: Optional[NetworkBuildOptions] = None,
    *,
    run_netconvert: bool = True,
) -> NetworkBuildResult:
    """Library entry point: VISUM SQLite -> SUMO ``net.xml`` + build report.

    Set ``run_netconvert=False`` to stop after emitting plain XML (useful when a
    SUMO build is unavailable). Raises :class:`VisumSQLiteError` on bad input.
    """
    options = options or NetworkBuildOptions()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    network = normalize_sqlite_network(sqlite_path, options)
    plain = write_plain_xml(network, out_dir)

    result = NetworkBuildResult(
        net_xml_path=None,
        netccfg_path=None,
        log_path=None,
        source_wkt=network.source_wkt,
        target_epsg=network.target_epsg,
        node_count=len(network.nodes),
        edge_count=len(network.edges),
        type_count=len(network.types),
        skipped_directions=network.skipped_directions,
        unmapped_tokens=network.unmapped_tokens,
        coherence_warnings=network.coherence_warnings,
        messages=list(network.messages),
    )

    if not run_netconvert:
        result.messages.append("netconvert skipped (run_netconvert=False)")
        return result

    net_path = out_dir / "net.net.xml"
    cfg_path = out_dir / "net.netccfg"
    log_path = out_dir / "netconvert.log"
    code = save_and_run(
        "netconvert",
        [
            "--node-files", plain["nod"].name,
            "--edge-files", plain["edg"].name,
            "--type-files", plain["typ"].name,
            "--tls.guess",
            "--output-file", net_path.name,
        ],
        cfg_path,
        out_dir,
        log_path,
    )
    result.netconvert_returncode = code
    result.netccfg_path = cfg_path if cfg_path.exists() else None
    result.log_path = log_path if log_path.exists() else None
    if code != 0:
        raise VisumSQLiteError(
            f"netconvert exited with code {code}; see log {log_path}"
        )
    result.net_xml_path = net_path if net_path.exists() else None
    return result
