# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Reachability-aware trip generation (fork replacement for od2trips edge sampling).

For each OMX ``tazRelation`` cell, sample ``(tazSource, tazSink)`` only from edge pairs
with a shortest path on ``net.xml`` for the target vClass. Preserves cell demand totals;
connector weights follow the od2trips independent-draw semantics (product of weights).
"""

from __future__ import annotations

import random
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import sumolib


class ReachableTripsError(Exception):
    """Fail-loud trip generation error (no viable connector pair for an O-D cell)."""


@dataclass(frozen=True)
class WeightedConnector:
    edge_id: str
    weight: float


@dataclass
class TazConnectors:
    sources: list[WeightedConnector] = field(default_factory=list)
    sinks: list[WeightedConnector] = field(default_factory=list)


@dataclass(frozen=True)
class TazRelationCell:
    origin: str
    destination: str
    count: float
    begin: float
    end: float
    vtype: str


@dataclass
class ReachableTripsResult:
    trips_path: Path
    trip_count: int = 0
    od_pairs_total: int = 0
    od_pairs_unreachable: int = 0
    messages: list[str] = field(default_factory=list)


def load_taz_connectors(tazs_path: str | Path) -> dict[str, TazConnectors]:
    """Parse ``tazs.xml`` into per-zone source/sink connector lists."""
    zones: dict[str, TazConnectors] = {}
    root = ET.parse(tazs_path).getroot()
    for elem in root.findall("taz"):
        zone_id = elem.get("id")
        if not zone_id:
            continue
        connectors = TazConnectors()
        for child in elem:
            edge_id = child.get("id")
            if not edge_id:
                continue
            weight = float(child.get("weight", "1") or "1")
            if child.tag == "tazSource":
                connectors.sources.append(WeightedConnector(edge_id, weight))
            elif child.tag == "tazSink":
                connectors.sinks.append(WeightedConnector(edge_id, weight))
        zones[zone_id] = connectors
    return zones


def load_taz_relations(taz_relation_path: str | Path) -> list[TazRelationCell]:
    """Parse ``tazRelation.xml`` intervals and relation cells."""
    root = ET.parse(taz_relation_path).getroot()
    cells: list[TazRelationCell] = []
    for interval in root.findall("interval"):
        vtype = interval.get("id", "")
        begin = float(interval.get("begin", "0"))
        end = float(interval.get("end", "86400"))
        for relation in interval.findall("tazRelation"):
            origin = relation.get("from")
            dest = relation.get("to")
            if not origin or not dest:
                continue
            cells.append(
                TazRelationCell(
                    origin=origin,
                    destination=dest,
                    count=float(relation.get("count", "0")),
                    begin=begin,
                    end=end,
                    vtype=vtype,
                )
            )
    return cells


@dataclass
class _ReachabilityIndex:
    net: sumolib.net.Net
    zones: dict[str, TazConnectors]
    vclass: str
    _pair_cache: dict[tuple[str, str], list[tuple[str, str, float]]] = field(default_factory=dict)
    _from_cache: dict[str, set[str]] = field(default_factory=dict)

    def _reachable_edge_ids_from(self, source_edge_id: str) -> set[str]:
        if source_edge_id in self._from_cache:
            return self._from_cache[source_edge_id]
        edge = self.net.getEdge(source_edge_id)
        if not edge.allows(self.vclass):
            reachable: set[str] = set()
        else:
            reachable = {item.getID() for item in self.net.getReachable(edge, vclass=self.vclass)}
        self._from_cache[source_edge_id] = reachable
        return reachable

    def viable_pairs(self, origin: str, destination: str) -> list[tuple[str, str, float]]:
        key = (origin, destination)
        if key in self._pair_cache:
            return self._pair_cache[key]
        origin_taz = self.zones.get(origin)
        dest_taz = self.zones.get(destination)
        if origin_taz is None or dest_taz is None:
            self._pair_cache[key] = []
            return []
        pairs: list[tuple[str, str, float]] = []
        for source in origin_taz.sources:
            reachable = self._reachable_edge_ids_from(source.edge_id)
            for sink in dest_taz.sinks:
                if sink.edge_id not in reachable:
                    continue
                to_edge = self.net.getEdge(sink.edge_id)
                if not to_edge.allows(self.vclass):
                    continue
                pairs.append((source.edge_id, sink.edge_id, source.weight * sink.weight))
        self._pair_cache[key] = pairs
        return pairs


def _vehicle_count(cell_count: float) -> int:
    """Deterministic OMX cell disaggregation (stable demand totals)."""
    return max(0, int(cell_count + 0.5))


def _sample_pair(
    pairs: list[tuple[str, str, float]],
    rng: random.Random,
) -> tuple[str, str]:
    total = sum(weight for _src, _sink, weight in pairs)
    if total <= 0:
        raise ReachableTripsError("internal error: empty weight sum for viable connector pairs")
    pick = rng.random() * total
    for source_id, sink_id, weight in pairs:
        pick -= weight
        if pick <= 0:
            return source_id, sink_id
    return pairs[-1][0], pairs[-1][1]


def _iter_trips(
    cells: list[TazRelationCell],
    index: _ReachabilityIndex,
    *,
    prefix: str,
    rng: random.Random,
) -> Iterator[tuple[str, float, str, str, str, str]]:
    """Yield (trip_id, depart, from_edge, to_edge, from_taz, to_taz)."""
    trip_num = 0
    for cell in cells:
        if cell.count <= 0:
            continue
        pairs = index.viable_pairs(cell.origin, cell.destination)
        if not pairs:
            raise ReachableTripsError(
                f"no viable connector pair for O-D relation {cell.origin}->{cell.destination} "
                f"(vType={cell.vtype!r}, count={cell.count:g})"
            )
        vehicles = _vehicle_count(cell.count)
        for _ in range(vehicles):
            source_id, sink_id = _sample_pair(pairs, rng)
            depart = rng.uniform(cell.begin, cell.end)
            yield (
                f"{prefix}{trip_num}",
                depart,
                source_id,
                sink_id,
                cell.origin,
                cell.destination,
            )
            trip_num += 1


def write_reachable_trips(
    net_xml: str | Path,
    tazs_path: str | Path,
    taz_relation_path: str | Path,
    trips_path: str | Path,
    *,
    vtype: str,
    prefix: str | None = None,
    depart_lane: str = "free",
    depart_speed: str = "max",
    seed: int | None = None,
) -> ReachableTripsResult:
    """Generate ``trips.xml`` with reachability-aware connector sampling."""
    net = sumolib.net.readNet(str(net_xml))
    zones = load_taz_connectors(tazs_path)
    cells = load_taz_relations(taz_relation_path)
    trip_prefix = prefix if prefix is not None else vtype
    rng = random.Random(seed)

    index = _ReachabilityIndex(net=net, zones=zones, vclass=vtype)
    result = ReachableTripsResult(trips_path=Path(trips_path))
    result.od_pairs_total = len({(c.origin, c.destination) for c in cells if c.count > 0})

    trips_path = Path(trips_path)
    trips_path.parent.mkdir(parents=True, exist_ok=True)
    with trips_path.open("w", encoding="utf-8", newline="\n") as out:
        out.write('<?xml version="1.0" encoding="UTF-8"?>\n\n')
        out.write("<routes>\n")
        for trip_id, depart, from_edge, to_edge, from_taz, to_taz in _iter_trips(
            cells, index, prefix=trip_prefix, rng=rng
        ):
            out.write(
                f'    <trip id="{trip_id}" depart="{depart:.2f}" '
                f'from="{from_edge}" to="{to_edge}" type="{vtype}" '
                f'fromTaz="{from_taz}" toTaz="{to_taz}" '
                f'departLane="{depart_lane}" departSpeed="{depart_speed}"/>\n'
            )
            result.trip_count += 1
        out.write("</routes>\n")
    return result


def expected_trip_count(cells: list[TazRelationCell]) -> int:
    """Total trips implied by relation cells using the same rounding as generation."""
    return sum(_vehicle_count(cell.count) for cell in cells if cell.count > 0)


def verify_trips_routable(
    net_xml: str | Path,
    trips_path: str | Path,
    *,
    vclass: str | None = None,
    limit: int | None = None,
) -> int:
    """Return count of trips with no shortest path (diagnostic helper)."""
    net = sumolib.net.readNet(str(net_xml))
    unroutable = 0
    seen = 0
    for _event, elem in ET.iterparse(trips_path, events=("end",)):
        if elem.tag != "trip":
            elem.clear()
            continue
        seen += 1
        if limit is not None and seen > limit:
            break
        vc = vclass or elem.get("type", "passenger")
        path, _ = net.getShortestPath(
            net.getEdge(elem.get("from")),
            net.getEdge(elem.get("to")),
            vClass=vc,
        )
        if not path:
            unroutable += 1
        elem.clear()
    return unroutable
