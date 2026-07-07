#!/usr/bin/env python3
# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later
"""Karlsruhe GTFS → SUMO PT on the SQLite-built net (turn-restricted)."""

from __future__ import annotations

import contextlib
import os
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO / "tools" / "import" / "gtfs"))
sys.path.insert(0, str(_REPO / "tools"))

import sumolib.net  # noqa: E402

# EPSG:25832 (Karlsruhe sqlite import target); origBoundary matches geojson net extent.
_PROJ = (
    "+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
)
_ORIG_BOUNDARY = "7.946000,48.443000,9.498000,49.479000"
_BBOX = "7.946,48.443,9.498,49.479"


def _patch_rtree_for_degenerate_edges() -> None:
    if getattr(sumolib.net.Net, "_gis_pt_rtree_patched", False):
        return

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


def _net_with_geo_projection(src: Path, dst: Path) -> Path:
    """Copy ``net.net.xml`` and attach a geo ``location`` for gtfs2pt."""
    text = src.read_text(encoding="utf-8")
    match = re.search(r"<location\b[^>]*/>", text)
    if not match:
        raise RuntimeError(f"No <location> in {src}")
    loc = match.group(0)
    # Preserve netOffset/convBoundary from build; replace geo fields only.
    net_offset_m = re.search(r'netOffset="([^"]*)"', loc)
    conv_m = re.search(r'convBoundary="([^"]*)"', loc)
    if not net_offset_m or not conv_m:
        raise RuntimeError(f"Unexpected location format in {src}")
    patched = (
        f'<location netOffset="{net_offset_m.group(1)}" '
        f'convBoundary="{conv_m.group(1)}" '
        f'origBoundary="{_ORIG_BOUNDARY}" projParameter="{_PROJ}"/>'
    )
    dst.write_text(text.replace(loc, patched, 1), encoding="utf-8")
    return dst


def main() -> int:
    _patch_rtree_for_degenerate_edges()
    os.environ.setdefault("SUMO_HOME", str(_REPO))
    import gtfs2pt  # noqa: E402

    home = Path.home() / "Downloads" / "Karlsruhe"
    out = Path(r"c:\tmp\karlsruhe-pt-sqlite")
    out.mkdir(parents=True, exist_ok=True)
    (out / "fcd").mkdir(exist_ok=True)
    (out / "netsplit").mkdir(exist_ok=True)

    net_src = Path(r"c:\tmp\karlsruhe\network\net.net.xml")
    net_pt = _net_with_geo_projection(net_src, out / "net.patched.xml")

    log = out / "gtfs2pt.log"
    args = [
        "-n",
        str(net_pt),
        "--gtfs",
        str(home / "google_transit.zip"),
        "--bbox",
        _BBOX,
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
    with open(log, "w", encoding="utf-8") as handle:
        with contextlib.redirect_stdout(handle), contextlib.redirect_stderr(handle):
            gtfs2pt.main(gtfs2pt.get_options(args))
    print(f"GTFS import log: {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
