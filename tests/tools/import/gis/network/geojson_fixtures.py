# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Builders for compact synthetic VISUM GeoJSON fixtures.

Each fixture encodes translation rules from
``openspec/changes/import-network-geojson/data-inventory.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

WGS84_CRS = {
    "type": "name",
    "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
}

# Karlsruhe-area WGS84 coordinates.
DEFAULT_NODES = {
    "1": (8.4010, 48.9940),
    "2": (8.4020, 48.9950),
    "3": (8.4035, 48.9965),
    "4": (8.4050, 48.9980),
}


def _point(node_id: str, lon: float, lat: float) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat, 0]},
        "properties": {
            "NO": int(node_id) if node_id.lstrip("-").isdigit() else node_id,
            "TYPENO": 2,
            "CONTROLTYPE": "0",
        },
    }


def _line(
    no: int,
    from_no: int,
    to_no: int,
    *,
    tsysset: str,
    r_tsysset: str | None = None,
    v0prt: str = "50km/h",
    r_v0prt: str | None = None,
    lc: str = "Collector",
    r_lc: str | None = None,
    typeno: int = 1,
    num_lanes: int = 2,
    r_num_lanes: int | None = None,
    coords: list[list[float]] | None = None,
) -> dict:
    if coords is None:
        coords = [
            list(DEFAULT_NODES[str(from_no)]),
            list(DEFAULT_NODES[str(to_no)]),
        ]
    props = {
        "NO": no,
        "FROMNODENO": from_no,
        "TONODENO": to_no,
        "TSYSSET": tsysset,
        "V0PRT": v0prt,
        "LC": lc,
        "TYPENO": typeno,
        "NUMLANES": num_lanes,
        "LENGTH": "0.100km",
        "R_NO": no,
        "R_FROMNODENO": to_no,
        "R_TONODENO": from_no,
        "R_TSYSSET": r_tsysset if r_tsysset is not None else tsysset,
        "R_V0PRT": r_v0prt if r_v0prt is not None else v0prt,
        "R_LC": r_lc if r_lc is not None else lc,
        "R_TYPENO": typeno,
        "R_NUMLANES": r_num_lanes if r_num_lanes is not None else num_lanes,
    }
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": props,
    }


DEFAULT_LINKS = [
    _line(100, 1, 2, tsysset="BIKE,CAR,HGV", v0prt="50km/h", lc="Collector"),
    _line(200, 2, 3, tsysset="BIKE,CAR,HGV", r_tsysset="", v0prt="50km/h"),
    _line(300, 3, 4, tsysset="BUS,TRAIN,TRAM", v0prt="0km/h", lc="PuT", typeno=8),
    _line(400, 1, 3, tsysset="CAR,HGV", v0prt="5km/h", lc="In-urban", num_lanes=1),
    _line(
        500,
        1,
        4,
        tsysset="BIKE,CAR,HGV",
        coords=[
            [8.4010, 48.9940],
            [8.4015, 48.9945],
            [8.4015, 48.9945],  # duplicate coordinate
            [8.4050, 48.9980],
        ],
        lc="Major",
    ),
    _line(600, 2, 4, tsysset="CAR,FERRY", v0prt="50km/h"),
    _line(700, 2, 4, tsysset="", r_tsysset=""),
]


def create_geojson(
    directory: str | Path,
    *,
    nodes=None,
    links=None,
    include_crs: bool = True,
    node_crs=None,
    link_crs=None,
) -> tuple[Path, Path]:
    """Write synthetic ``node.geojson`` and ``link.geojson``; return their paths."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    nodes = DEFAULT_NODES if nodes is None else nodes
    links = DEFAULT_LINKS if links is None else links

    node_fc = {
        "type": "FeatureCollection",
        "features": [_point(nid, lon, lat) for nid, (lon, lat) in nodes.items()],
    }
    link_fc = {
        "type": "FeatureCollection",
        "features": links,
    }
    if include_crs:
        node_fc["crs"] = node_crs or WGS84_CRS
        link_fc["crs"] = link_crs or WGS84_CRS

    node_path = directory / "node.geojson"
    link_path = directory / "link.geojson"
    node_path.write_text(json.dumps(node_fc), encoding="utf-8")
    link_path.write_text(json.dumps(link_fc), encoding="utf-8")
    return node_path, link_path


def write_malformed_link(path: Path) -> Path:
    path.write_text("{ this is not valid json", encoding="utf-8")
    return path


def write_missing_crs(directory: Path) -> tuple[Path, Path]:
    return create_geojson(directory, include_crs=False)
