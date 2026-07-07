#!/usr/bin/env python
# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later
"""Karlsruhe GTFS → SUMO PT smoke runner (gtfs2pt with degenerate-edge workaround)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO / "tools" / "import" / "gtfs"))
sys.path.insert(0, str(_REPO / "tools"))

import sumolib.net  # noqa: E402


def _patch_rtree_for_degenerate_edges() -> None:
    """Skip zero-area edges that break sumolib R-tree (VISUM net artefacts)."""
    if getattr(sumolib.net.Net, "_gis_pt_rtree_patched", False):
        return
    _orig = sumolib.net.Net._initRTree

    def _initRTree_safe(self, edges, includeJunctions):
        import rtree.index

        result = rtree.index.Index()
        for ri, shape in enumerate(edges):
            try:
                result.add(ri, shape.getBoundingBox(includeJunctions))
            except AssertionError:
                continue
        return result

    sumolib.net.Net._initRTree = _initRTree_safe
    sumolib.net.Net._gis_pt_rtree_patched = True


def main() -> int:
    _patch_rtree_for_degenerate_edges()
    os.environ.setdefault("SUMO_HOME", str(_REPO))
    import gtfs2pt  # noqa: E402

    home = Path.home() / "Downloads" / "Karlsruhe"
    out = Path(r"c:\tmp\karlsruhe-pt")
    out.mkdir(parents=True, exist_ok=True)
    (out / "fcd").mkdir(exist_ok=True)
    (out / "netsplit").mkdir(exist_ok=True)

    args = [
        "-n",
        r"c:\tmp\karlsruhe-geojson-net\net.net.xml",
        "--gtfs",
        str(home / "google_transit.zip"),
        "--date",
        "20260625",
        "--modes",
        "bus,tram",
        "--additional-output",
        str(out / "pt.add.xml"),
        "--route-output",
        str(out / "pt.rou.xml"),
        "--vtype-output",
        str(out / "vtypes.xml"),
        "--fcd",
        str(out / "fcd"),
        "--network-split",
        str(out / "netsplit"),
        "--sort",
        "--verbose",
        "--warn-unmapped",
    ]
    gtfs2pt.main(gtfs2pt.get_options(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
