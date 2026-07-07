#!/usr/bin/env python3
"""Compare two Karlsruhe gtfs2pt outputs (vehicle/stop counts, unmapped routes)."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _count_vehicles(rou_path: Path) -> dict[str, int]:
    tree = ET.parse(rou_path)
    counts: dict[str, int] = {}
    for elem in tree.getroot():
        if elem.tag == "vehicle":
            vtype = elem.get("type", "?")
            counts[vtype] = counts.get(vtype, 0) + 1
    return counts


def _count_stops(add_path: Path) -> dict[str, int]:
    tree = ET.parse(add_path)
    counts: dict[str, int] = {}
    for elem in tree.getroot():
        if elem.tag in ("busStop", "trainStop"):
            counts[elem.tag] = counts.get(elem.tag, 0) + 1
    return counts


def _unmapped_routes(log_path: Path) -> list[str]:
    if not log_path.is_file():
        return []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    routes = []
    for line in text.splitlines():
        if "unmapped" in line.lower() or "Could not map" in line:
            routes.append(line.strip())
        m = re.search(r"route[^:]*:\s*(\S+)", line, re.I)
        if m and ("warn" in line.lower() or "skip" in line.lower()):
            routes.append(line.strip())
    return routes


def _summarize(label: Path) -> dict:
    base = label
    rou = base / "pt.rou.xml"
    add = base / "pt.add.xml"
    log = base / "gtfs2pt.log"
    return {
        "dir": str(base),
        "vehicles": _count_vehicles(rou) if rou.is_file() else {},
        "stops": _count_stops(add) if add.is_file() else {},
        "vehicle_total": sum(_count_vehicles(rou).values()) if rou.is_file() else 0,
        "unmapped_lines": _unmapped_routes(log),
    }


def main() -> int:
    old = Path(r"c:\tmp\karlsruhe-pt")
    new = Path(r"c:\tmp\karlsruhe-pt-sqlite")
    for name, data in [("geojson-net (before)", old), ("sqlite-net (turn-filtered)", new)]:
        print(f"=== {name} ===")
        if not (data / "pt.rou.xml").is_file():
            print("  (no pt.rou.xml — import missing or failed)")
            continue
        s = _summarize(data)
        print(f"  vehicles: {s['vehicles']}  total={s['vehicle_total']}")
        print(f"  stops: {s['stops']}")
        unmapped = s["unmapped_lines"]
        print(f"  unmapped/warn lines in log: {len(unmapped)}")
        for line in unmapped[:15]:
            print(f"    {line}")
        if len(unmapped) > 15:
            print(f"    ... +{len(unmapped) - 15} more")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
