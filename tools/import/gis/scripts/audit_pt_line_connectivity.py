#!/usr/bin/env python3
# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later
"""Audit GTFS line connectivity on the SQLite-built Karlsruhe SUMO net."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd
import sumolib

_BBOX = (7.946, 48.443, 9.498, 49.479)  # W,S,E,N — same as gtfs2pt import


def _gtfs_lines_in_bbox(gtfs_zip: Path) -> dict[str, dict]:
    """GTFS routes with at least one stop inside the network bbox."""
    with zipfile.ZipFile(gtfs_zip) as zf:
        stops = pd.read_csv(zf.open("stops.txt"))
        routes = pd.read_csv(zf.open("routes.txt"))
        trips = pd.read_csv(zf.open("trips.txt"))
        stop_times = pd.read_csv(zf.open("stop_times.txt"))

    w, s, e, n = _BBOX
    in_bbox = stops[
        (stops["stop_lon"] >= w)
        & (stops["stop_lon"] <= e)
        & (stops["stop_lat"] >= s)
        & (stops["stop_lat"] <= n)
    ]
    stop_ids = set(in_bbox["stop_id"])
    st = stop_times[stop_times["stop_id"].isin(stop_ids)]
    trip_ids = set(st["trip_id"])
    tr = trips[trips["trip_id"].isin(trip_ids)]
    route_ids = set(tr["route_id"])
    eligible = routes[routes["route_id"].isin(route_ids)].copy()

    out: dict[str, dict] = {}
    for _, row in eligible.iterrows():
        rid = str(row["route_id"])
        short = str(row.get("route_short_name", rid))
        rtype = int(row["route_type"])
        mode = {0: "tram", 3: "bus"}.get(rtype, "other")
        out[rid] = {
            "route_id": rid,
            "short_name": short,
            "route_type": rtype,
            "mode": mode,
            "trip_count": int((tr["route_id"] == row["route_id"]).sum()),
        }
    return out


def _parse_not_mapped(log_path: Path) -> dict[str, list[str]]:
    """Trip ids from gtfs2pt log that failed map-matching."""
    if not log_path.is_file():
        return {}
    by_line: dict[str, list[str]] = defaultdict(list)
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"Not mapped (\S+)", line)
        if not m:
            continue
        trip_key = m.group(1)
        route_name = _route_name_from_trip_key(trip_key)
        by_line[route_name].append(trip_key)
    return dict(by_line)


def _route_name_from_trip_key(trip_key: str) -> str:
    """Extract GTFS short route id from gtfs2pt vehicle key (T0.agency-route-...)."""
    m = re.search(r"\.T0\.[^-]+-([^-]+)-", trip_key)
    return m.group(1) if m else trip_key


def _load_routes(rou_path: Path) -> dict[str, list[str]]:
    routes: dict[str, list[str]] = {}
    for elem in ET.parse(rou_path).getroot():
        if elem.tag == "route":
            edges = (elem.get("edges") or "").split()
            routes[elem.get("id", "")] = [e for e in edges if e]
    return routes


def _load_vehicles(rou_path: Path) -> list[dict]:
    vehicles = []
    for elem in ET.parse(rou_path).getroot():
        if elem.tag != "vehicle":
            continue
        route_id = elem.get("route", "")
        line = elem.get("line", "")
        vtype = elem.get("type", "")
        route_name = line.split("#")[0] if line else ""
        for child in elem:
            if child.tag == "param" and child.get("key") == "gtfs.route_name":
                route_name = child.get("value", route_name)
        vehicles.append(
            {
                "id": elem.get("id", ""),
                "route_ref": route_id,
                "line": route_name,
                "type": vtype,
            }
        )
    return vehicles


def _edges_connected(net: sumolib.net.Net, edges: list[str]) -> list[tuple[str, str]]:
    """Return disconnected consecutive pairs (empty if fully connected)."""
    gaps: list[tuple[str, str]] = []
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1]
        try:
            from_edge = net.getEdge(a)
        except Exception:
            gaps.append((a, b))
            continue
        outgoing = {e.getID() for e in from_edge.getOutgoing().keys()}
        if b not in outgoing:
            gaps.append((a, b))
    return gaps


def main() -> int:
    net_path = Path(r"c:\tmp\karlsruhe\network\net.net.xml")
    rou_path = Path(r"c:\tmp\karlsruhe-pt-sqlite\pt.rou.xml")
    log_path = Path(r"c:\tmp\karlsruhe-pt-sqlite\gtfs2pt.log")
    gtfs_zip = Path.home() / "Downloads" / "Karlsruhe" / "google_transit.zip"

    if len(sys.argv) > 1:
        net_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        rou_path = Path(sys.argv[2])

    print("Loading net:", net_path)
    net = sumolib.net.readNet(str(net_path))
    eligible = _gtfs_lines_in_bbox(gtfs_zip)
    bus_tram = {
        rid: info
        for rid, info in eligible.items()
        if info["mode"] in ("bus", "tram")
    }

    routes = _load_routes(rou_path)
    vehicles = _load_vehicles(rou_path)
    not_mapped = _parse_not_mapped(log_path)

    # Per GTFS short_name aggregate (bus+tram only)
    by_name: dict[str, dict] = defaultdict(
        lambda: {
            "mode": "",
            "vehicles": 0,
            "connected": 0,
            "disconnected": 0,
            "single_edge": 0,
            "gaps": [],
            "not_mapped_trips": 0,
            "route_ids": set(),
        }
    )

    for info in bus_tram.values():
        name = info["short_name"]
        by_name[name]["mode"] = info["mode"]
        by_name[name]["route_ids"].add(info["route_id"])

    for veh in vehicles:
        if veh["type"] not in ("bus", "tram"):
            continue
        name = veh["line"]
        edges = routes.get(veh["route_ref"], [])
        by_name[name]["vehicles"] += 1
        if len(edges) <= 1:
            by_name[name]["single_edge"] += 1
            by_name[name]["connected"] += 1
            continue
        gaps = _edges_connected(net, edges)
        if gaps:
            by_name[name]["disconnected"] += 1
            if len(by_name[name]["gaps"]) < 3:
                by_name[name]["gaps"].extend(gaps[: 3 - len(by_name[name]["gaps"])])
        else:
            by_name[name]["connected"] += 1

    for name, trips in not_mapped.items():
        if name in by_name:
            by_name[name]["not_mapped_trips"] += len(trips)

    # Eligible short names present in GTFS bbox filter
    eligible_names = {info["short_name"] for info in bus_tram.values()}

    mapped_names = {n for n, d in by_name.items() if d["vehicles"] > 0}
    no_vehicle = sorted(eligible_names - mapped_names)
    disconnected_lines = []
    partial_unmapped = []
    fully_ok = []

    for name in sorted(eligible_names, key=lambda x: (by_name[x]["mode"], x)):
        d = by_name[name]
        has_veh = d["vehicles"] > 0
        has_nm = d["not_mapped_trips"] > 0
        has_disc = d["disconnected"] > 0
        if not has_veh and not has_nm:
            no_vehicle.append(name)
        elif has_disc:
            disconnected_lines.append((name, d))
        elif has_nm and has_veh:
            partial_unmapped.append((name, d))
        elif has_nm and not has_veh:
            pass  # counted below as unmapped_only
        elif has_veh:
            fully_ok.append(name)

    unmapped_only = [
        name
        for name in eligible_names
        if by_name[name]["vehicles"] == 0 and by_name[name]["not_mapped_trips"] > 0
    ]
    no_trace_no_nm = [
        name
        for name in eligible_names
        if by_name[name]["vehicles"] == 0 and by_name[name]["not_mapped_trips"] == 0
    ]

    print()
    print("=== GTFS lines in bbox (bus+tram) ===")
    print(f"  eligible routes: {len(bus_tram)}  distinct short names: {len(eligible_names)}")
    print(f"  with SUMO vehicles: {len(mapped_names)}")
    print()
    print("=== Connectivity of mapped routes (consecutive edges in net.xml) ===")
    print(f"  lines with ALL vehicles connected: {len(fully_ok)}")
    print(f"  lines with ANY disconnected vehicle route: {len(disconnected_lines)}")
    if disconnected_lines:
        print("  (unexpected — gtfs2pt routes should be connected)")
        for name, d in disconnected_lines[:10]:
            print(f"    {d['mode']} {name}: {d['disconnected']}/{d['vehicles']} trips broken", d["gaps"][:2])
    print()
    print("=== Map-matching failures (gtfs2pt 'Not mapped') ===")
    nm_total = sum(by_name[n]["not_mapped_trips"] for n in eligible_names)
    print(f"  not-mapped trip instances in log: {nm_total}")
    print(f"  lines with zero vehicles but some not-mapped trips: {len(unmapped_only)}")
    for name in sorted(unmapped_only, key=lambda n: -by_name[n]["not_mapped_trips"])[:20]:
        d = by_name[name]
        print(f"    {d['mode']} line {name}: {d['not_mapped_trips']} trips not mapped")
    if len(unmapped_only) > 20:
        print(f"    ... +{len(unmapped_only) - 20} more")
    print()
    print("=== Partial viability (some trips map, some fail) ===")
    for name, d in sorted(partial_unmapped, key=lambda x: -x[1]["not_mapped_trips"])[:15]:
        print(
            f"    {d['mode']} line {name}: mapped {d['vehicles']} vehicles, "
            f"not mapped {d['not_mapped_trips']} trips"
        )
    print()
    print("=== No SUMO vehicles and no 'Not mapped' log entry ===")
    print(f"  count: {len(no_trace_no_nm)} (likely filtered by mode/date or empty trace)")
    if no_trace_no_nm[:15]:
        print("   ", ", ".join(sorted(no_trace_no_nm)[:15]))

    non_viable = sorted(
        set(unmapped_only) | {n for n, d in disconnected_lines} | set(no_trace_no_nm),
        key=lambda x: (by_name[x]["mode"], x),
    )
    print()
    print("=== Summary: lines NOT fully viable on sqlite net ===")
    print(f"  {len(non_viable)} of {len(eligible_names)} short names have issues")
    viable = len(eligible_names) - len(non_viable)
    print(f"  {viable} lines appear fully viable (all in-bbox trips mapped + connected)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
