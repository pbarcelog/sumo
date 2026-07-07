# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Synthetic VISUM GeoJSON zone/connector fixtures for demand import tests."""

from __future__ import annotations

import json
from pathlib import Path

from .fixtures import (
    BIKE_ONLY_INTRAZONAL_ZONE,
    DEAD_CONNECTOR_ZONE,
    ONE_WAY_CONNECTOR_ZONE,
    PUT_ONLY_ZONE,
    ZONE_IDS,
)

WGS84_CRS = {
    "type": "name",
    "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
}

# WGS84 coords near Karlsruhe (aligned with network geojson fixtures).
ZONE_COORDS = {
    "10": (8.4010, 48.9940),
    "20": (8.4020, 48.9950),
    "30": (8.4035, 48.9965),
    PUT_ONLY_ZONE: (8.4050, 48.9980),
    DEAD_CONNECTOR_ZONE: (8.4040, 48.9970),
    BIKE_ONLY_INTRAZONAL_ZONE: (8.4045, 48.9975),
    ONE_WAY_CONNECTOR_ZONE: (8.4030, 48.9960),
    "15": (8.4015, 48.9945),
}

NODE_COORDS = {
    1: (8.4010, 48.9940),
    2: (8.4020, 48.9950),
    3: (8.4035, 48.9965),
    4: (8.4050, 48.9980),
    99: (8.4045, 48.9975),
    6: (8.4012, 48.9942),
    7: (8.4018, 48.9946),
}


def _zone_point(zone_id: str) -> dict:
    lon, lat = ZONE_COORDS[zone_id]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat, 0]},
        "properties": {"NO": int(zone_id), "NAME": f"zone_{zone_id}"},
    }


def _connector_line(
    zoneno: int,
    nodeno: int,
    *,
    tsysset: str,
    r_tsysset: str | None = None,
    r_direction: str | None = "D",
    reverse: bool = True,
) -> dict:
    z_lon, z_lat = ZONE_COORDS.get(str(zoneno), (8.4010, 48.9940))
    n_lon, n_lat = NODE_COORDS.get(nodeno, (8.4010, 48.9940))
    ba_direction = r_direction if r_direction is not None else ("D" if reverse else "")
    ba_tsysset = tsysset if r_tsysset is None else r_tsysset
    if not ba_direction:
        ba_tsysset = ""
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[z_lon, z_lat, 0], [n_lon, n_lat, 0]],
        },
        "properties": {
            "ZONENO": zoneno,
            "NODENO": nodeno,
            "DIRECTION": "O",
            "TSYSSET": tsysset,
            "R_ZONENO": zoneno,
            "R_NODENO": nodeno,
            "R_DIRECTION": ba_direction,
            "R_TSYSSET": ba_tsysset if ba_direction else "",
        },
    }


def create_demand_geojson(
    directory: str | Path,
    *,
    include_put_only_zone: bool = True,
    include_dead_connector_zone: bool = False,
    include_bike_only_intrazonal_zone: bool = False,
    include_one_way_connector_zone: bool = False,
    include_split_reachability_zone: bool = False,
    include_empty_tsysset_direction: bool = False,
) -> tuple[Path, Path]:
    """Write ``zone_centroid.geojson`` and ``connector.geojson`` for demand tests."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    zone_ids = list(ZONE_IDS)
    if include_put_only_zone:
        zone_ids.append(PUT_ONLY_ZONE)
    if include_dead_connector_zone:
        zone_ids.append(DEAD_CONNECTOR_ZONE)
    if include_bike_only_intrazonal_zone:
        zone_ids.append(BIKE_ONLY_INTRAZONAL_ZONE)
    if include_one_way_connector_zone:
        zone_ids.append(ONE_WAY_CONNECTOR_ZONE)
    if include_split_reachability_zone:
        zone_ids.append("15")

    connectors = [
        _connector_line(10, 1, tsysset="BIKE,CAR,HGV,WALK"),
        _connector_line(20, 2, tsysset="BIKE,CAR,HGV,WALK"),
        _connector_line(30, 3, tsysset="BIKE,CAR,HGV,WALK"),
        _connector_line(10, 2, tsysset="BIKE,CAR,HGV,WALK", reverse=False, r_direction=""),
    ]
    if include_put_only_zone:
        connectors.append(_connector_line(int(PUT_ONLY_ZONE), 4, tsysset="PUTW"))
    if include_dead_connector_zone:
        connectors.append(_connector_line(int(DEAD_CONNECTOR_ZONE), 99, tsysset="CAR"))
    if include_bike_only_intrazonal_zone:
        connectors.append(
            _connector_line(int(BIKE_ONLY_INTRAZONAL_ZONE), 99, tsysset="BIKE,CAR")
        )
    if include_one_way_connector_zone:
        connectors.append(
            _connector_line(
                int(ONE_WAY_CONNECTOR_ZONE),
                3,
                tsysset="BIKE,CAR,HGV,WALK",
                r_direction="",
                r_tsysset="",
            )
        )
    if include_split_reachability_zone:
        connectors.append(
            _connector_line(10, 6, tsysset="CAR,HGV", reverse=False, r_direction="")
        )
    if include_empty_tsysset_direction:
        connectors.append(
            _connector_line(30, 4, tsysset="", r_tsysset="CAR", r_direction="D")
        )

    zone_fc = {
        "type": "FeatureCollection",
        "crs": WGS84_CRS,
        "features": [_zone_point(zone_id) for zone_id in zone_ids],
    }
    connector_fc = {
        "type": "FeatureCollection",
        "crs": WGS84_CRS,
        "features": connectors,
    }
    zone_path = directory / "zone_centroid.geojson"
    connector_path = directory / "connector.geojson"
    zone_path.write_text(json.dumps(zone_fc), encoding="utf-8")
    connector_path.write_text(json.dumps(connector_fc), encoding="utf-8")
    return zone_path, connector_path


def write_malformed_connector(path: Path) -> Path:
    path.write_text("{ not valid json", encoding="utf-8")
    return path


def write_connector_unknown_zone(directory: Path) -> tuple[Path, Path]:
    zone_path, _ = create_demand_geojson(directory)
    connector_fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[8.4010, 48.9940, 0], [8.4010, 48.9940, 0]],
                },
                "properties": {
                    "ZONENO": 99999,
                    "NODENO": 1,
                    "DIRECTION": "O",
                    "TSYSSET": "CAR",
                    "R_ZONENO": 99999,
                    "R_NODENO": 1,
                    "R_DIRECTION": "D",
                    "R_TSYSSET": "CAR",
                },
            },
        ],
    }
    connector_path = directory / "connector.geojson"
    connector_path.write_text(json.dumps(connector_fc), encoding="utf-8")
    return zone_path, connector_path
