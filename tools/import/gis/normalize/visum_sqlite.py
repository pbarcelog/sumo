# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Read a VISUM SQLite network export and normalize it for ``netconvert``.

Implements the ``network-import-sqlite`` capability: table discovery/validation,
CRS reprojection from the embedded ``NETWORK.PROJECTIONDEFINITION`` WKT, directed
``LINK``-row pairing (AB = ``NO`` / BA = ``-NO``), mode -> ``vClass`` permission
translation, ``LINKTYPE``-driven per-mode speed resolution, and ``LINKPOLY``
geometry reconstruction.

Translation rules are normative in ``import-network-sqlite/data-inventory.md``.
This module performs no subprocess work; ``orchestrate/netbuild.py`` consumes the
:class:`NormalizedNetwork` it produces.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional

from .modes import DEFAULT_MODE_MAPPING, map_tsysset
from .speed import DEFAULT_LOW_SPEED_THRESHOLD_KMH, resolve_edge_speed

REQUIRED_TABLES = {"NETWORK", "NODE", "LINK", "LINKTYPE", "TSYS"}
OPTIONAL_TABLES = {"LINKPOLY", "MODE", "ZONE", "CONNECTOR"}
DEFERRED_TABLES = {
    "STOP", "STOPPOINT", "STOPAREA", "LINE", "LINEROUTE", "LINEROUTEITEM",
    "TIMEPROFILE", "TIMEPROFILEITEM", "VEHJOURNEY", "VEHJOURNEYITEM",
    "TURN", "LANETURN", "FARESYSTEM", "FAREMODEL", "SIGNALCONTROL",
}

DEFAULT_TARGET_EPSG = "EPSG:25832"


@dataclass
class NetworkBuildOptions:
    """Options for a VISUM SQLite network build (data-inventory sections 4-8)."""

    mode_mapping: dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_MODE_MAPPING)
    )
    crs: str = DEFAULT_TARGET_EPSG
    source_crs: Optional[str] = None
    low_speed_threshold_kmh: float = DEFAULT_LOW_SPEED_THRESHOLD_KMH


@dataclass
class NodeRecord:
    node_id: str
    x: float
    y: float


@dataclass
class EdgeRecord:
    edge_id: str
    from_node: str
    to_node: str
    type_id: str
    num_lanes: int
    speed_ms: float
    allow: list[str]
    shape: list[tuple[float, float]]


@dataclass
class EdgeTypeDef:
    type_id: str
    speed_ms: float
    restrictions_ms: dict[str, float] = field(default_factory=dict)


@dataclass
class NormalizedNetwork:
    nodes: list[NodeRecord] = field(default_factory=list)
    edges: list[EdgeRecord] = field(default_factory=list)
    types: dict[str, EdgeTypeDef] = field(default_factory=dict)
    source_wkt: Optional[str] = None
    target_epsg: str = DEFAULT_TARGET_EPSG
    deferred_tables: list[str] = field(default_factory=list)
    skipped_directions: list[str] = field(default_factory=list)
    unmapped_tokens: dict[str, int] = field(default_factory=dict)
    coherence_warnings: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def record(self, message: str) -> None:
        self.messages.append(message)


class VisumSQLiteError(RuntimeError):
    """Raised on unreadable input, missing tables, or unresolvable CRS."""


def _table_names(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
    ).fetchall()
    return {str(r[0]).upper(): str(r[0]) for r in rows}


def discover_tables(conn: sqlite3.Connection) -> dict[str, object]:
    """Validate required tables and classify optional/deferred ones."""
    available = _table_names(conn)
    missing = sorted(REQUIRED_TABLES - set(available))
    if missing:
        raise VisumSQLiteError(
            f"VISUM SQLite export is missing required table(s): {', '.join(missing)}"
        )
    deferred = sorted(set(available) & DEFERRED_TABLES)
    return {
        "available": available,
        "deferred": deferred,
        "has_linkpoly": "LINKPOLY" in available,
    }


def _make_transformer(conn: sqlite3.Connection, options: NetworkBuildOptions):
    from pyproj import CRS, Transformer

    source = options.source_crs
    wkt = None
    row = conn.execute("SELECT PROJECTIONDEFINITION FROM NETWORK").fetchone()
    if row is not None and row[0]:
        wkt = str(row[0])
    crs_value = source or wkt
    if not crs_value:
        raise VisumSQLiteError(
            "VISUM SQLite source CRS is missing (NETWORK.PROJECTIONDEFINITION "
            "empty); supply build_options.source_crs"
        )
    try:
        src_crs = CRS.from_user_input(crs_value)
    except Exception as exc:  # pyproj raises several exception types
        raise VisumSQLiteError(f"Could not parse VISUM source CRS: {exc}") from exc
    transformer = Transformer.from_crs(src_crs, options.crs, always_xy=True)
    return transformer, (source or wkt)


def normalize_sqlite_network(
    sqlite_path: str | Path,
    options: Optional[NetworkBuildOptions] = None,
) -> NormalizedNetwork:
    """Read and normalize a VISUM SQLite export into network records."""
    options = options or NetworkBuildOptions()
    path = Path(sqlite_path)
    if not path.is_file():
        raise VisumSQLiteError(f"VISUM SQLite path is not a file: {path}")

    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise VisumSQLiteError(f"Could not open SQLite database: {exc}") from exc

    try:
        conn.row_factory = sqlite3.Row
        try:
            discovery = discover_tables(conn)
        except sqlite3.DatabaseError as exc:
            raise VisumSQLiteError(f"Not a readable SQLite database: {exc}") from exc

        result = NormalizedNetwork(target_epsg=options.crs)
        result.deferred_tables = list(discovery["deferred"])
        for table in result.deferred_tables:
            result.record(f"Deferred table reported (not imported): {table}")

        transformer, source_crs = _make_transformer(conn, options)
        result.source_wkt = source_crs

        node_xy = _read_nodes(conn, transformer, result)
        linkpolys = (
            _read_linkpolys(conn, transformer) if discovery["has_linkpoly"] else {}
        )
        linktypes = _read_linktypes(conn)

        _build_edges(conn, options, node_xy, linkpolys, linktypes, result)
        return result
    finally:
        conn.close()


def _read_nodes(conn, transformer, result: NormalizedNetwork) -> dict[str, tuple[float, float]]:
    node_xy: dict[str, tuple[float, float]] = {}
    for row in conn.execute("SELECT NO, XCOORD, YCOORD FROM NODE"):
        if row["XCOORD"] is None or row["YCOORD"] is None:
            continue
        node_id = str(int(row["NO"]))
        x, y = transformer.transform(float(row["XCOORD"]), float(row["YCOORD"]))
        node_xy[node_id] = (x, y)
        result.nodes.append(NodeRecord(node_id=node_id, x=x, y=y))
    return node_xy


def _read_linkpolys(conn, transformer) -> dict[tuple[str, str], list[tuple[float, float]]]:
    polys: dict[tuple[str, str], list[tuple[float, float]]] = {}
    rows = conn.execute(
        'SELECT FROMNODENO, TONODENO, "INDEX", XCOORD, YCOORD FROM LINKPOLY '
        'ORDER BY FROMNODENO, TONODENO, "INDEX"'
    )
    for row in rows:
        key = (str(int(row["FROMNODENO"])), str(int(row["TONODENO"])))
        x, y = transformer.transform(float(row["XCOORD"]), float(row["YCOORD"]))
        polys.setdefault(key, []).append((x, y))
    return polys


def _read_linktypes(conn) -> dict[str, dict[str, object]]:
    types: dict[str, dict[str, object]] = {}
    for row in conn.execute("SELECT * FROM LINKTYPE"):
        mapping = {k: row[k] for k in row.keys()}
        types[str(int(row["NO"]))] = mapping
    return types


def _link_geometry(
    from_node: str,
    to_node: str,
    node_xy: Mapping[str, tuple[float, float]],
    linkpolys: Mapping[tuple[str, str], list[tuple[float, float]]],
) -> list[tuple[float, float]]:
    if (from_node, to_node) in linkpolys:
        mid = linkpolys[(from_node, to_node)]
    elif (to_node, from_node) in linkpolys:
        mid = list(reversed(linkpolys[(to_node, from_node)]))
    else:
        mid = []
    return [node_xy[from_node], *mid, node_xy[to_node]]


def _build_edges(conn, options, node_xy, linkpolys, linktypes, result: NormalizedNetwork) -> None:
    tsys_to_vclass = {str(k).upper(): str(v) for k, v in options.mode_mapping.items()}

    # Group directed rows by NO; deterministic AB/BA from (FROMNODENO, TONODENO).
    grouped: dict[int, list[sqlite3.Row]] = {}
    columns_checked = False
    for row in conn.execute("SELECT * FROM LINK"):
        if not columns_checked:
            required = {"NO", "FROMNODENO", "TONODENO", "TSYSSET", "TYPENO", "NUMLANES", "V0PRT"}
            missing = required - set(row.keys())
            if missing:
                raise VisumSQLiteError(
                    f"LINK table missing required column(s): {', '.join(sorted(missing))}"
                )
            columns_checked = True
        grouped.setdefault(int(row["NO"]), []).append(row)

    for no in sorted(grouped):
        rows = sorted(grouped[no], key=lambda r: (int(r["FROMNODENO"]), int(r["TONODENO"])))
        ab = rows[0]
        ba = next(
            (
                r
                for r in rows[1:]
                if int(r["FROMNODENO"]) == int(ab["TONODENO"])
                and int(r["TONODENO"]) == int(ab["FROMNODENO"])
            ),
            None,
        )
        _emit_direction(no, ab, +1, options, tsys_to_vclass, node_xy, linkpolys, linktypes, result)
        if ba is not None:
            _emit_direction(no, ba, -1, options, tsys_to_vclass, node_xy, linkpolys, linktypes, result)


def _emit_direction(
    no, row, sign, options, tsys_to_vclass, node_xy, linkpolys, linktypes, result: NormalizedNetwork
) -> None:
    tsysset = row["TSYSSET"]
    from_node = str(int(row["FROMNODENO"]))
    to_node = str(int(row["TONODENO"]))
    direction = "AB" if sign > 0 else "BA"

    vclasses, unmapped = map_tsysset(tsysset, options.mode_mapping)
    for token in unmapped:
        result.unmapped_tokens[token] = result.unmapped_tokens.get(token, 0) + 1

    if not vclasses:
        # Empty (or fully-unmapped) transport set: skip this direction, logged.
        result.skipped_directions.append(f"{no}:{direction}")
        return

    if from_node not in node_xy or to_node not in node_xy:
        result.record(f"Link {no}:{direction} references missing node coordinates; skipped")
        result.skipped_directions.append(f"{no}:{direction}")
        return

    type_id = str(int(row["TYPENO"]))
    linktype_row = linktypes.get(type_id, {})
    resolution = resolve_edge_speed(
        vclasses,
        linktype_row,
        tsys_to_vclass,
        v0prt_kmh=row["V0PRT"],
        low_speed_threshold_kmh=options.low_speed_threshold_kmh,
    )
    if resolution.coherence_warning:
        result.coherence_warnings.append(
            f"{no}:{direction} ceiling={resolution.ceiling_kmh:g}km/h "
            f"type={type_id} allow={' '.join(vclasses)}"
        )

    num_lanes = int(row["NUMLANES"]) if row["NUMLANES"] else 1
    num_lanes = max(num_lanes, 1)
    edge_id = str(no) if sign > 0 else f"-{no}"
    shape = _link_geometry(from_node, to_node, node_xy, linkpolys)

    result.edges.append(
        EdgeRecord(
            edge_id=edge_id,
            from_node=from_node,
            to_node=to_node,
            type_id=type_id,
            num_lanes=num_lanes,
            speed_ms=resolution.speed_ms,
            allow=vclasses,
            shape=shape,
        )
    )
    _register_type(result, type_id, resolution)


def _register_type(result: NormalizedNetwork, type_id: str, resolution) -> None:
    existing = result.types.get(type_id)
    restrictions_ms = {
        vclass: kmh / 3.6 for vclass, kmh in resolution.restrictions_kmh.items()
    }
    if existing is None:
        result.types[type_id] = EdgeTypeDef(
            type_id=type_id,
            speed_ms=resolution.speed_ms,
            restrictions_ms=restrictions_ms,
        )
        return
    existing.speed_ms = max(existing.speed_ms, resolution.speed_ms)
    for vclass, speed in restrictions_ms.items():
        existing.restrictions_ms.setdefault(vclass, speed)
