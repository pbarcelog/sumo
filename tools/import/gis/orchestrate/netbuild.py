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

from gis.normalize.visum_geojson import (
    GeoJsonBuildOptions,
    VisumGeoJsonError,
    normalize_geojson_network,
)
from gis.normalize.visum_sqlite import (
    NetworkBuildOptions,
    NormalizedNetwork,
    VisumSQLiteError,
    normalize_sqlite_network,
)
from gis.normalize.visum_turns import (
    TurnConnection,
    TurnResolutionResult,
    read_turn_connections,
    turn_patch_for_net,
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
    speed_substitutions: list = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    netconvert_returncode: Optional[int] = None
    resolved_epsg: Optional[str] = None
    turn_connection_count: int = 0
    turn_via_nodes: int = 0
    turn_deleted_connections: int = 0
    turn_unresolved_targets: int = 0


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


def write_connections_xml(
    additions: list[TurnConnection],
    out_dir: Path,
    prefix: str = "net",
    *,
    deletes: Optional[list[TurnConnection]] = None,
) -> Optional[Path]:
    """Write SUMO ``*.con.xml`` patch file; return path or ``None`` if empty."""
    deletes = deletes or []
    if not additions and not deletes:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    con_path = out_dir / f"{prefix}.con.xml"
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<connections>"]
    for conn in additions:
        lines.append(
            f'    <connection from={quoteattr(conn.from_edge)} to={quoteattr(conn.to_edge)}/>'
        )
    for conn in deletes:
        lines.append(
            f'    <delete from={quoteattr(conn.from_edge)} to={quoteattr(conn.to_edge)}/>'
        )
    lines.append("</connections>")
    con_path.write_text("\n".join(lines), encoding="utf-8")
    return con_path


def write_geojson_plain_xml(
    network: NormalizedNetwork, out_dir: Path, prefix: str = "net"
) -> dict[str, Path]:
    """Write WGS84 plain XML for ``netconvert --proj.utm`` (speed on edges)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    nod_path = out_dir / f"{prefix}.nod.xml"
    edg_path = out_dir / f"{prefix}.edg.xml"

    nod_lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<nodes>"]
    for node in network.nodes:
        nod_lines.append(
            f'    <node id={quoteattr(node.node_id)} x="{_fmt(node.x)}" y="{_fmt(node.y)}"/>'
        )
    nod_lines.append("</nodes>")
    nod_path.write_text("\n".join(nod_lines), encoding="utf-8")

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

    return {"nod": nod_path, "edg": edg_path}


def _infer_utm_epsg(network: NormalizedNetwork) -> str:
    if not network.nodes:
        return "EPSG:25832"
    lon = sum(n.x for n in network.nodes) / len(network.nodes)
    lat = sum(n.y for n in network.nodes) / len(network.nodes)
    zone = int((lon + 180) // 6) + 1
    if lat >= 0:
        return f"EPSG:{32600 + zone}"
    return f"EPSG:{32700 + zone}"


def _parse_epsg_from_log(log_path: Path) -> Optional[str]:
    if not log_path.is_file():
        return None
    text = log_path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if "EPSG:" in line:
            start = line.find("EPSG:")
            fragment = line[start:].split()[0].strip(".,;")
            if fragment.startswith("EPSG:"):
                return fragment
    return None


def _network_build_result(network: NormalizedNetwork) -> NetworkBuildResult:
    return NetworkBuildResult(
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
        speed_substitutions=list(network.speed_substitutions),
        messages=list(network.messages),
    )


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

    turn_result = read_turn_connections(sqlite_path, network.edges)
    allowed_con_path: Optional[Path] = None
    if turn_result.via_nodes:
        allowed_con_path = write_connections_xml(
            turn_result.connections, out_dir, prefix="net.turn-allowed"
        )
        network.record(
            f"TURN import: {len(turn_result.connections)} allowed movements at "
            f"{len(turn_result.via_nodes)} junctions"
        )
        for message in turn_result.messages:
            network.record(message)

    result = _network_build_result(network)
    if turn_result.via_nodes:
        result.turn_connection_count = len(turn_result.connections)
        result.turn_via_nodes = len(turn_result.via_nodes)
        result.turn_unresolved_targets = turn_result.unresolved_targets
        result.messages.extend(turn_result.messages)

    if not run_netconvert:
        result.messages.append("netconvert skipped (run_netconvert=False)")
        return result

    net_path = out_dir / "net.net.xml"
    cfg_path = out_dir / "net.netccfg"
    log_path = out_dir / "netconvert.log"
    build_args = [
        "--node-files", plain["nod"].name,
        "--edge-files", plain["edg"].name,
        "--type-files", plain["typ"].name,
    ]
    if allowed_con_path is not None:
        build_args.extend(["--connection-files", allowed_con_path.name])
    build_args.extend(["--tls.guess", "--output-file", net_path.name])
    code = save_and_run(
        "netconvert",
        build_args,
        cfg_path,
        out_dir,
        log_path,
    )
    result.netconvert_returncode = code
    if code != 0:
        raise VisumSQLiteError(
            f"netconvert exited with code {code}; see log {log_path}"
        )

    if turn_result.via_nodes:
        _additions, deletes = turn_patch_for_net(net_path, turn_result)
        result.turn_deleted_connections = len(deletes)
        patch_path = write_connections_xml(
            [], out_dir, prefix="net.turn-patch", deletes=deletes
        )
        if patch_path is not None:
            patch_log = out_dir / "netconvert.turns.log"
            patch_cfg = out_dir / "net.turn-patch.netccfg"
            patch_code = save_and_run(
                "netconvert",
                [
                    "--sumo-net-file", net_path.name,
                    "--connection-files", patch_path.name,
                    "--output-file", net_path.name,
                ],
                patch_cfg,
                out_dir,
                patch_log,
            )
            result.netconvert_returncode = patch_code
            result.log_path = patch_log if patch_log.exists() else result.log_path
            if patch_code != 0:
                raise VisumSQLiteError(
                    f"netconvert turn patch exited with code {patch_code}; "
                    f"see log {patch_log}"
                )
        result.messages.append(
            f"TURN patch: removed {len(deletes)} connections not in VISUM TURN"
        )

    result.netccfg_path = cfg_path if cfg_path.exists() else None
    if result.log_path is None and log_path.exists():
        result.log_path = log_path
    result.net_xml_path = net_path if net_path.exists() else None
    return result


def build_network_from_geojson(
    nodes_path: str | Path,
    links_path: str | Path,
    out_dir: str | Path,
    options: Optional[GeoJsonBuildOptions] = None,
    *,
    run_netconvert: bool = True,
) -> NetworkBuildResult:
    """Library entry point: VISUM GeoJSON -> SUMO ``net.xml`` + build report.

    Input geometry is WGS84; ``netconvert`` projects with ``--proj.utm``.
    Raises :class:`VisumGeoJsonError` on bad input or failed build.
    """
    options = options or GeoJsonBuildOptions()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    network = normalize_geojson_network(nodes_path, links_path, options)
    plain = write_geojson_plain_xml(network, out_dir)
    result = _network_build_result(network)
    result.resolved_epsg = _infer_utm_epsg(network)
    result.messages.append(
        f"Inferred UTM projection {result.resolved_epsg} from node centroid"
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
            "--proj.utm",
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
    parsed = _parse_epsg_from_log(log_path)
    if parsed:
        result.resolved_epsg = parsed
        result.messages.append(f"netconvert resolved projection {parsed}")
    if code != 0:
        raise VisumGeoJsonError(
            f"netconvert exited with code {code}; see log {log_path}"
        )
    result.net_xml_path = net_path if net_path.exists() else None
    return result
