# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""VISUM ``ZONE`` / ``CONNECTOR`` → SUMO ``tazs.xml`` (ADR-014)."""

from __future__ import annotations

from dataclasses import dataclass, field
import sqlite3
from pathlib import Path
import xml.sax.saxutils as saxutils

import sumolib

from gis.normalize.demand_totals import ZoneDemandTotals
from gis.normalize.modes import map_tsysset, split_tsysset

DEFAULT_CORE_CONNECTOR_TOKEN: dict[str, str] = {
    "Car": "CAR",
    "HVG": "HGV",
}

PRT_TSYS_TOKENS = frozenset({"CAR", "HGV", "BIKE", "WALK"})

ConnectorRow = tuple[int, int, str, str]  # ZONENO, NODENO, DIRECTION, TSYSSET


class VisumZonesError(Exception):
    """Fail-loud demand / connector resolution error."""


@dataclass
class TazRecord:
    taz_id: str
    sources: list[str] = field(default_factory=list)
    sinks: list[str] = field(default_factory=list)


@dataclass
class TazBuildResult:
    core: str
    vtype: str
    tazs_path: Path
    records: list[TazRecord] = field(default_factory=list)
    excluded_zones: list[str] = field(default_factory=list)
    unmapped_tokens: dict[str, int] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    zone_access: dict[str, tuple[bool, bool]] = field(default_factory=dict)


@dataclass
class ZoneConnectorTables:
    zone_ids: set[str]
    connectors: list[ConnectorRow]
    put_only_zones: set[str]


def read_zone_connectors(sqlite_path: str | Path) -> ZoneConnectorTables:
    conn = sqlite3.connect(str(sqlite_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT NO FROM ZONE")
        zone_ids = {str(row[0]) for row in cur.fetchall()}
        cur.execute("SELECT ZONENO, NODENO, DIRECTION, TSYSSET FROM CONNECTOR")
        connectors = [(row[0], row[1], row[2], row[3] or "") for row in cur.fetchall()]
    finally:
        conn.close()

    put_only_zones: set[str] = set()
    for zone_id in zone_ids:
        zone_connectors = [c for c in connectors if str(c[0]) == zone_id]
        if not zone_connectors:
            continue
        if all(
            not (set(split_tsysset(tsys)) & PRT_TSYS_TOKENS)
            for _, _, _, tsys in zone_connectors
        ):
            put_only_zones.add(zone_id)
    return ZoneConnectorTables(
        zone_ids=zone_ids,
        connectors=connectors,
        put_only_zones=put_only_zones,
    )


def _incident_edge_ids(net: sumolib.net.Net, node_id: int | str, direction: str, vclass: str) -> list[str]:
    nid = str(node_id)
    edge_ids: list[str] = []
    if direction == "O":
        for edge in net.getEdges():
            if edge.getFromNode().getID() != nid or not edge.allows(vclass):
                continue
            if len(edge.getOutgoing()) == 0:
                continue
            edge_ids.append(edge.getID())
    elif direction == "D":
        for edge in net.getEdges():
            if edge.getToNode().getID() != nid or not edge.allows(vclass):
                continue
            if len(edge.getIncoming()) == 0:
                continue
            edge_ids.append(edge.getID())
    else:
        raise VisumZonesError(f"unknown connector direction {direction!r}")
    return sorted(set(edge_ids))


def _connector_matches_token(tsysset: str, token: str) -> bool:
    return token.upper() in split_tsysset(tsysset)


def _mode_connectors(zone_connectors: list[ConnectorRow], connector_token: str) -> list[ConnectorRow]:
    return [c for c in zone_connectors if _connector_matches_token(c[3], connector_token)]


def _synthesize_missing_direction(
    zone_id: str,
    mode_connectors: list[ConnectorRow],
    *,
    need_direction: str,
    existing_direction: str,
    messages: list[str],
) -> list[ConnectorRow]:
    """Mirror every connector on ``existing_direction`` to ``need_direction`` (same node, TSYSSET)."""
    existing = [c for c in mode_connectors if c[2] == existing_direction]
    if not existing:
        return mode_connectors
    missing = [c for c in mode_connectors if c[2] == need_direction]
    if missing:
        return mode_connectors
    synthesized = [
        (zoneno, nodeno, need_direction, tsys)
        for zoneno, nodeno, _, tsys in existing
    ]
    messages.append(
        f"zone {zone_id}: synthesized {len(synthesized)} {need_direction} connector(s) "
        f"from {existing_direction} (mode-filtered)"
    )
    return mode_connectors + synthesized


def _resolve_zone_edges(
    connectors: list[ConnectorRow],
    net: sumolib.net.Net,
    vtype: str,
    unmapped: dict[str, int],
) -> tuple[set[str], set[str]]:
    sources: set[str] = set()
    sinks: set[str] = set()
    for _, nodeno, direction, tsys in connectors:
        _, unmapped_tokens = map_tsysset(tsys)
        for token in unmapped_tokens:
            unmapped[token] = unmapped.get(token, 0) + 1
        for edge_id in _incident_edge_ids(net, nodeno, direction, vtype):
            if direction == "O":
                sources.add(edge_id)
            else:
                sinks.add(edge_id)
    return sources, sinks


def build_taz_records_for_core(
    tables: ZoneConnectorTables,
    net: sumolib.net.Net,
    *,
    core: str,
    vtype: str,
    connector_token: str,
    demand_totals: dict[str, ZoneDemandTotals],
    zero_demand_zone_ids: set[str],
) -> tuple[list[TazRecord], list[str], dict[str, int], dict[str, tuple[bool, bool]], list[str]]:
    unmapped: dict[str, int] = {}
    excluded: list[str] = []
    records: list[TazRecord] = []
    zone_access: dict[str, tuple[bool, bool]] = {}
    messages: list[str] = []

    for zone_id in sorted(tables.zone_ids, key=lambda value: int(value)):
        zone_connectors = [c for c in tables.connectors if str(c[0]) == zone_id]
        if zone_id in tables.put_only_zones and zone_id in zero_demand_zone_ids:
            excluded.append(zone_id)
            zone_access[zone_id] = (False, False)
            continue

        totals = demand_totals.get(zone_id, ZoneDemandTotals())
        mode_connectors = _mode_connectors(zone_connectors, connector_token)

        if totals.needs_inbound:
            mode_connectors = _synthesize_missing_direction(
                zone_id,
                mode_connectors,
                need_direction="D",
                existing_direction="O",
                messages=messages,
            )
        if totals.needs_outbound:
            mode_connectors = _synthesize_missing_direction(
                zone_id,
                mode_connectors,
                need_direction="O",
                existing_direction="D",
                messages=messages,
            )

        sources, sinks = _resolve_zone_edges(mode_connectors, net, vtype, unmapped)
        zone_access[zone_id] = (bool(sources), bool(sinks))

        if totals.needs_outbound and not sources:
            raise VisumZonesError(
                f"zone {zone_id} ({core}) has external production but no resolvable tazSource edges"
            )
        if totals.needs_inbound and not sinks:
            raise VisumZonesError(
                f"zone {zone_id} ({core}) has external attraction but no resolvable tazSink edges"
            )

        if not sources and not sinks:
            excluded.append(zone_id)
            continue

        records.append(
            TazRecord(
                taz_id=zone_id,
                sources=sorted(sources),
                sinks=sorted(sinks),
            )
        )

    return records, excluded, unmapped, zone_access, messages


def write_tazs_xml(records: list[TazRecord], output_path: Path) -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<tazs>"]
    for record in records:
        lines.append(f'    <taz id={saxutils.quoteattr(record.taz_id)}>')
        for edge_id in record.sources:
            lines.append(f'        <tazSource id={saxutils.quoteattr(edge_id)} weight="1"/>')
        for edge_id in record.sinks:
            lines.append(f'        <tazSink id={saxutils.quoteattr(edge_id)} weight="1"/>')
        lines.append("    </taz>")
    lines.append("</tazs>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_tazs_for_core(
    sqlite_path: str | Path,
    net_xml: str | Path,
    output_path: str | Path,
    *,
    core: str,
    vtype: str,
    connector_token: str | None = None,
    demand_totals: dict[str, ZoneDemandTotals] | None = None,
    zero_demand_zone_ids: set[str] | None = None,
) -> TazBuildResult:
    token = connector_token or DEFAULT_CORE_CONNECTOR_TOKEN[core]
    tables = read_zone_connectors(sqlite_path)
    net = sumolib.net.readNet(str(net_xml))
    demand_totals = demand_totals or {}
    zero_demand_zone_ids = zero_demand_zone_ids or set()

    records, excluded, unmapped, zone_access, messages = build_taz_records_for_core(
        tables,
        net,
        core=core,
        vtype=vtype,
        connector_token=token,
        demand_totals=demand_totals,
        zero_demand_zone_ids=zero_demand_zone_ids,
    )
    out = Path(output_path)
    write_tazs_xml(records, out)
    return TazBuildResult(
        core=core,
        vtype=vtype,
        tazs_path=out,
        records=records,
        excluded_zones=sorted(set(excluded), key=int),
        unmapped_tokens=unmapped,
        messages=messages,
        zone_access=zone_access,
    )
