#!/usr/bin/env python
# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later
"""Analyze trips with no shortest path on the built net (Karlsruhe diagnostic)."""

from __future__ import annotations

import argparse
import sqlite3
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import sumolib


def _depart_dead_end(net: sumolib.net.Net, edge_id: str, vclass: str) -> bool:
    edge = net.getEdge(edge_id)
    if not edge.allows(vclass):
        return True
    return len(edge.getOutgoing()) == 0


def _arrive_dead_end(net: sumolib.net.Net, edge_id: str, vclass: str) -> bool:
    edge = net.getEdge(edge_id)
    if not edge.allows(vclass):
        return True
    return len(edge.getIncoming()) == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--net", required=True)
    parser.add_argument("--trips", action="append", required=True)
    parser.add_argument("--sample", type=int, default=50000)
    args = parser.parse_args()

    net = sumolib.net.readNet(args.net)
    no_path = 0
    intra_no = inter_no = 0
    intra_total = inter_total = 0
    dead_depart = dead_arrive = 0
    reasons = Counter()
    examples: list[str] = []

    for trip_file in args.trips:
        for _, elem in ET.iterparse(trip_file, events=("end",)):
            if elem.tag != "trip":
                continue
            vclass = elem.get("type", "passenger")
            from_taz = elem.get("fromTaz", "")
            to_taz = elem.get("toTaz", "")
            intra = from_taz == to_taz
            if intra:
                intra_total += 1
            else:
                inter_total += 1
            fe = net.getEdge(elem.get("from"))
            te = net.getEdge(elem.get("to"))
            path, _ = net.getShortestPath(fe, te, vClass=vclass)
            if path:
                elem.clear()
                continue
            no_path += 1
            if intra:
                intra_no += 1
            else:
                inter_no += 1
            if _depart_dead_end(net, elem.get("from"), vclass):
                dead_depart += 1
                reasons["depart_no_outgoing"] += 1
            elif _arrive_dead_end(net, elem.get("to"), vclass):
                dead_arrive += 1
                reasons["arrive_no_incoming"] += 1
            else:
                reasons["disconnected_subgraph"] += 1
            if len(examples) < 5:
                examples.append(
                    f"{elem.get('id')} {vclass} intra={intra} "
                    f"{from_taz}->{to_taz} {elem.get('from')}->{elem.get('to')}"
                )
            elem.clear()

    total = intra_total + inter_total
    print(f"trips scanned: {total}")
    print(f"intrazonal: {intra_total}  interzonal: {inter_total}")
    print(f"no shortest path: {no_path} ({100 * no_path / max(total, 1):.3f}%)")
    print(f"  intrazonal unroutable: {intra_no} ({100 * intra_no / max(intra_total, 1):.2f}%)")
    print(f"  interzonal unroutable: {inter_no} ({100 * inter_no / max(inter_total, 1):.2f}%)")
    print(f"depart edge has no outgoing: {dead_depart}")
    print(f"arrive edge has no incoming: {dead_arrive}")
    print("reasons:", dict(reasons))
    print("examples:")
    for line in examples:
        print(" ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
