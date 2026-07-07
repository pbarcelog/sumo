# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Map VISUM ``TURN`` rows to SUMO connection whitelist entries.

VISUM defines allowed movements at a junction (via node) as
``FROMNODENO -> VIANODENO -> TONODENO``. SUMO edge ids follow the SQLite
network convention (``NO`` / ``-NO``). For junctions present in ``TURN``,
every incoming edge whose ``to`` node is that via node is restricted to the
movements listed in the table; approaches with no matching turns are blocked.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional, Sequence

from .visum_sqlite import EdgeRecord, VisumSQLiteError


@dataclass(frozen=True)
class TurnConnection:
    """Edge-to-edge connection allowed at a junction."""

    from_edge: str
    to_edge: str


@dataclass
class TurnResolutionResult:
    connections: list[TurnConnection] = field(default_factory=list)
    turn_map: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    via_nodes: set[str] = field(default_factory=set)
    turn_rows: int = 0
    turn_rows_imported: int = 0
    turn_rows_skipped: int = 0
    blocked_approaches: int = 0
    unresolved_targets: int = 0
    messages: list[str] = field(default_factory=list)

    def record(self, message: str) -> None:
        self.messages.append(message)


def _pair_index(edges: Sequence[EdgeRecord]) -> dict[tuple[str, str], list[str]]:
    index: dict[tuple[str, str], list[str]] = defaultdict(list)
    for edge in edges:
        index[(edge.from_node, edge.to_node)].append(edge.edge_id)
    for key in index:
        index[key].sort()
    return index


def _import_turn_row(from_node: str, via_node: str, to_node: str, tsysset: Optional[str]) -> bool:
    """Return whether a ``TURN`` row applies to the motorized network import."""
    if from_node == to_node:
        return False
    if not (tsysset or "").strip():
        return False
    return True


def _read_turn_map(
    conn: sqlite3.Connection,
) -> tuple[dict[tuple[str, str], set[str]], set[str], int, int, int]:
    """Return ``(from,via) -> {to}``, via nodes, and row counts."""
    turn_map: dict[tuple[str, str], set[str]] = defaultdict(set)
    via_nodes: set[str] = set()
    row_count = 0
    imported = 0
    skipped = 0
    try:
        rows = conn.execute(
            "SELECT FROMNODENO, VIANODENO, TONODENO, TSYSSET FROM TURN"
        )
    except sqlite3.Error as exc:
        raise VisumSQLiteError(f"Could not read TURN table: {exc}") from exc

    for row in rows:
        row_count += 1
        from_node = str(int(row[0]))
        via_node = str(int(row[1]))
        to_node = str(int(row[2]))
        tsysset = row[3]
        if not _import_turn_row(from_node, via_node, to_node, tsysset):
            skipped += 1
            continue
        imported += 1
        turn_map[(from_node, via_node)].add(to_node)
        via_nodes.add(via_node)
    return turn_map, via_nodes, row_count, imported, skipped


def resolve_turn_connections(
    edges: Sequence[EdgeRecord],
    turn_map: Mapping[tuple[str, str], set[str]],
    via_nodes: Iterable[str],
) -> TurnResolutionResult:
    """Resolve VISUM turns against built edges."""
    result = TurnResolutionResult()
    result.turn_rows = sum(len(v) for v in turn_map.values())
    result.via_nodes = set(via_nodes)
    pair_index = _pair_index(edges)
    seen: set[tuple[str, str]] = set()

    for edge in edges:
        via = edge.to_node
        if via not in result.via_nodes:
            continue
        key = (edge.from_node, via)
        to_nodes = turn_map.get(key, set())
        if not to_nodes:
            result.blocked_approaches += 1
            continue

        resolved_any = False
        for to_node in sorted(to_nodes):
            outgoing = pair_index.get((via, to_node), [])
            if not outgoing:
                result.unresolved_targets += 1
                continue
            for to_edge in outgoing:
                pair = (edge.edge_id, to_edge)
                if pair in seen:
                    continue
                seen.add(pair)
                result.connections.append(TurnConnection(edge.edge_id, to_edge))
                resolved_any = True
        if not resolved_any:
            result.blocked_approaches += 1
            result.record(
                f"No resolvable turns for approach {edge.edge_id} "
                f"({edge.from_node}->{via}); junction will block this edge"
            )

    return result


def read_turn_connections(
    sqlite_path: str,
    edges: Sequence[EdgeRecord],
) -> TurnResolutionResult:
    """Read ``TURN`` from SQLite and resolve SUMO connections."""
    try:
        conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise VisumSQLiteError(f"Could not open SQLite database: {exc}") from exc

    try:
        tables = {
            str(r[0]).upper()
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            )
        }
        if "TURN" not in tables:
            result = TurnResolutionResult()
            result.record("TURN table not present; skipping turn import")
            return result
        turn_map, via_nodes, row_count, imported, skipped = _read_turn_map(conn)
        result = resolve_turn_connections(edges, turn_map, via_nodes)
        result.turn_map = dict(turn_map)
        result.turn_rows = row_count
        result.turn_rows_imported = imported
        result.turn_rows_skipped = skipped
        if skipped:
            result.record(
                f"TURN filter: skipped {skipped} row(s) with empty TSYSSET "
                f"or same from/to node (PuT-walk / reversal rows)"
            )
        return result
    finally:
        conn.close()


def connections_by_from_edge(
    connections: Sequence[TurnConnection],
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for conn in connections:
        grouped[conn.from_edge].append(conn.to_edge)
    for from_edge in grouped:
        grouped[from_edge] = sorted(set(grouped[from_edge]))
    return grouped


def approaches_needing_block(
    edges: Sequence[EdgeRecord],
    via_nodes: Iterable[str],
    turn_map: Mapping[tuple[str, str], set[str]],
    grouped: Mapping[str, list[str]],
) -> list[str]:
    """Incoming edges at controlled junctions with no allowed outgoing movement."""
    via_set = set(via_nodes)
    blocked: list[str] = []
    for edge in edges:
        if edge.to_node not in via_set:
            continue
        key = (edge.from_node, edge.to_node)
        if key not in turn_map:
            blocked.append(edge.edge_id)
            continue
        if edge.edge_id not in grouped:
            blocked.append(edge.edge_id)
    return blocked


def turn_patch_for_net(
    net_path: str | Path,
    turn_result: TurnResolutionResult,
) -> tuple[list[TurnConnection], list[TurnConnection]]:
    """Return ``(additions, deletions)`` to align ``net.xml`` with VISUM ``TURN``."""
    import sumolib

    allowed = {(c.from_edge, c.to_edge) for c in turn_result.connections}
    current: set[tuple[str, str]] = set()
    deletes: list[TurnConnection] = []
    seen_delete: set[tuple[str, str]] = set()
    net = sumolib.net.readNet(str(net_path))
    for junction_id in sorted(turn_result.via_nodes, key=int):
        if junction_id not in net._id2node:
            turn_result.record(
                f"TURN via node {junction_id} not present in built net; skipped"
            )
            continue
        node = net.getNode(junction_id)
        for edge in node.getIncoming():
            from_edge_id = edge.getID()
            from_node = edge.getFromNode().getID()
            key = (from_node, junction_id)
            for to_edge, _conns in edge.getOutgoing().items():
                to_id = to_edge.getID()
                pair = (from_edge_id, to_id)
                current.add(pair)
                if pair in seen_delete:
                    continue
                if key not in turn_result.turn_map or pair not in allowed:
                    seen_delete.add(pair)
                    deletes.append(TurnConnection(from_edge_id, to_id))

    additions = [
        TurnConnection(from_edge, to_edge)
        for from_edge, to_edge in sorted(allowed - current)
    ]
    return additions, deletes
