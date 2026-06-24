#!/usr/bin/env python
# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later
"""Rebuild Karlsruhe demand artifacts (tazs + trips) after connector fix."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

import sumolib

from gis.orchestrate.demand import DemandBuildOptions, build_demand_from_visum

OMX = Path(os.environ.get("KARLSRUHE_OMX", ""))
SQLITE = Path(os.environ.get("KARLSRUHE_SQLITE", ""))
NET = Path(os.environ.get("KARLSRUHE_NET", r"c:\tmp\karlsruhe\network\net.net.xml"))
OUT = Path(r"c:\tmp\karlsruhe\demand")


def main() -> int:
    build_demand_from_visum(
        OMX,
        SQLITE,
        NET,
        OUT,
        DemandBuildOptions(run_duarouter=False),
    )
    tazs = (OUT / "tazs.passenger.xml").read_text(encoding="utf-8")
    block_start = tazs.index('id="1000018"')
    block_end = tazs.index("</taz>", block_start)
    print(tazs[block_start:block_end + 6])
    print("zone 1000018 lists -550081510:", "-550081510" in tazs[block_start:block_end])

    net = sumolib.net.readNet(str(NET))
    dead = 0
    n = 0
    for _, el in ET.iterparse(OUT / "trips.passenger.xml", events=("end",)):
        if el.tag != "trip":
            continue
        n += 1
        if n > 200000:
            break
        if len(net.getEdge(el.get("from")).getOutgoing()) == 0:
            dead += 1
        el.clear()
    print(f"dead depart in 200k passenger trips: {dead}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
