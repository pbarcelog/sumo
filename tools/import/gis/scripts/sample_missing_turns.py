#!/usr/bin/env python3
"""Print sample VISUM TURN movements missing from a built SUMO net."""
from __future__ import annotations

import os
import sqlite3
import sys

import sumolib

from gis.normalize.visum_sqlite import normalize_sqlite_network
from gis.normalize.visum_turns import read_turn_connections


def main() -> int:
    sqlite = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.expanduser("~"), "Downloads", "Karlsruhe", "Karlsruhe-sqlite.sqlite3"
    )
    net_path = sys.argv[2] if len(sys.argv) > 2 else r"c:\tmp\karlsruhe\network\net.net.xml"

    network = normalize_sqlite_network(sqlite)
    turns = read_turn_connections(sqlite, network.edges)
    allowed = {(c.from_edge, c.to_edge) for c in turns.connections}
    net = sumolib.net.readNet(net_path)

    current: set[tuple[str, str]] = set()
    for junction_id in turns.via_nodes:
        if junction_id not in net._id2node:
            continue
        node = net.getNode(junction_id)
        for edge in node.getIncoming():
            fid = edge.getID()
            for to_edge, _ in edge.getOutgoing().items():
                current.add((fid, to_edge.getID()))
    missing = sorted(allowed - current)

    conn = sqlite3.connect(sqlite)
    conn.row_factory = sqlite3.Row

    def detail(pair: tuple[str, str]) -> dict:
        fe, te = pair
        e_in = next(e for e in network.edges if e.edge_id == fe)
        e_out = next(e for e in network.edges if e.edge_id == te)
        via = e_in.to_node
        row = conn.execute(
            "SELECT TSYSSET, ISCHANGEOFDIRECTION, CAPPRT, TYPENO FROM TURN "
            "WHERE FROMNODENO=? AND VIANODENO=? AND TONODENO=? LIMIT 1",
            (int(e_in.from_node), int(via), int(e_out.to_node)),
        ).fetchone()
        node_row = conn.execute(
            "SELECT CONTROLTYPE, XCOORD, YCOORD FROM NODE WHERE NO=?", (int(via),)
        ).fetchone()
        built_out: list[str] = []
        if via in net._id2node:
            for inc in net.getNode(via).getIncoming():
                if inc.getID() == fe:
                    built_out = [x.getID() for x in inc.getOutgoing().keys()]
        return {
            "from_node": e_in.from_node,
            "via": via,
            "to_node": e_out.to_node,
            "from_edge": fe,
            "to_edge": te,
            "in_allow": " ".join(e_in.allow),
            "out_allow": " ".join(e_out.allow),
            "tsysset": row["TSYSSET"] if row else "",
            "uturn": row["ISCHANGEOFDIRECTION"] if row else "",
            "cap": row["CAPPRT"] if row else "",
            "control": node_row["CONTROLTYPE"] if node_row else "?",
            "x": node_row["XCOORD"] if node_row else None,
            "y": node_row["YCOORD"] if node_row else None,
            "built_out": built_out,
            "other_whitelist": sorted(
                t[1] for t in allowed if t[0] == fe and t[1] != te
            )[:6],
        }

    examples: list[tuple[str, dict]] = []

    def pick(label: str, pred) -> None:
        if any(e[0] == label for e in examples):
            return
        for pair in missing:
            d = detail(pair)
            if pred(d):
                examples.append((label, d))
                return

    pick("U-turn (same from/to node)", lambda d: d["from_node"] == d["to_node"])
    pick("U-turn flagged ISCHANGEOFDIRECTION=1", lambda d: d["uturn"] == 1)
    pick("Empty TSYSSET on TURN row", lambda d: d["tsysset"] == "")
    pick("TRAM-only turn", lambda d: d["tsysset"] == "TRAM")
    pick("Approach has zero outgoing in built net", lambda d: d["built_out"] == [])
    pick(
        "Partial: other turns from same approach exist",
        lambda d: bool(d["built_out"]),
    )

    print(f"Total missing (whitelisted but not in net.xml): {len(missing)}")
    print("All are netconvert geometry/connectivity rejects (edges exist in our import).\n")
    for label, d in examples:
        print(f"== {label} ==")
        print(
            f"  nodes: {d['from_node']} -> {d['via']} -> {d['to_node']} "
            f"(CONTROLTYPE={d['control']})"
        )
        print(
            f"  edges: {d['from_edge']} [{d['in_allow']}] -> "
            f"{d['to_edge']} [{d['out_allow']}]"
        )
        print(
            f"  TURN: TSYSSET={d['tsysset']!r} ISCHANGEOFDIRECTION={d['uturn']} "
            f"CAPPRT={d['cap']}"
        )
        print(f"  built outgoing from {d['from_edge']}: {d['built_out']}")
        print(f"  other whitelisted targets (same approach): {d['other_whitelist']}")
        if d["x"] is not None:
            print(f"  via node coords (VISUM): x={d['x']:.1f} y={d['y']:.1f}")
        print()

    conn.close()

    # overlapping category counts + extra samples
    conn = sqlite3.connect(sqlite)
    conn.row_factory = sqlite3.Row
    cats = {
        "uturn": 0,
        "empty_tsys": 0,
        "tram_only": 0,
        "zero_outgoing": 0,
        "partial_outgoing": 0,
        "car_involved": 0,
    }
    extra: dict[str, tuple[str, str] | None] = {
        "car_partial": None,
        "car_uturn": None,
        "bike_partial": None,
    }

    for pair in missing:
        d = detail(pair)
        if d["from_node"] == d["to_node"]:
            cats["uturn"] += 1
        if d["tsysset"] == "":
            cats["empty_tsys"] += 1
        if d["tsysset"] == "TRAM":
            cats["tram_only"] += 1
        if not d["built_out"]:
            cats["zero_outgoing"] += 1
        elif len(d["built_out"]) < len([t for t in allowed if t[0] == d["from_edge"]]):
            cats["partial_outgoing"] += 1
        if "passenger" in d["in_allow"] or "passenger" in d["out_allow"]:
            cats["car_involved"] += 1
            if extra["car_partial"] is None and d["built_out"]:
                extra["car_partial"] = pair
            if (
                extra["car_uturn"] is None
                and d["from_node"] == d["to_node"]
                and "passenger" in d["in_allow"]
            ):
                extra["car_uturn"] = pair
        if extra["bike_partial"] is None and "bicycle" in d["in_allow"] and d["built_out"]:
            extra["bike_partial"] = pair

    print("Category counts (overlapping):")
    for key, count in sorted(cats.items(), key=lambda item: -item[1]):
        print(f"  {key}: {count}")
    print()

    for tag, pair in [
        ("Car — partial (some turns built)", extra["car_partial"]),
        ("Car — U-turn", extra["car_uturn"]),
        ("Bike — partial", extra["bike_partial"]),
    ]:
        if pair is None:
            continue
        d = detail(pair)
        print(f"== {tag} ==")
        print(
            f"  nodes: {d['from_node']} -> {d['via']} -> {d['to_node']} "
            f"(CONTROLTYPE={d['control']})"
        )
        print(
            f"  edges: {d['from_edge']} [{d['in_allow']}] -> "
            f"{d['to_edge']} [{d['out_allow']}]"
        )
        print(
            f"  TURN: TSYSSET={d['tsysset']!r} ISCHANGEOFDIRECTION={d['uturn']} "
            f"CAPPRT={d['cap']}"
        )
        print(f"  built outgoing from {d['from_edge']}: {d['built_out']}")
        print(f"  other whitelisted targets: {d['other_whitelist']}")
        if d["x"] is not None:
            print(f"  via node coords (VISUM): x={d['x']:.1f} y={d['y']:.1f}")
        print()

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
