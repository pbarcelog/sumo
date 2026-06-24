# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Synthetic OMX + SQLite ZONE/CONNECTOR fixtures for demand import tests."""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import numpy as np

pytest = __import__("pytest")
openmatrix = pytest.importorskip("openmatrix")

from gis.normalize.demand_totals import ZoneDemandTotals

_network_fixtures_path = Path(__file__).resolve().parent.parent / "network" / "fixtures.py"
_spec = importlib.util.spec_from_file_location("network_fixtures", _network_fixtures_path)
assert _spec and _spec.loader
_network_fixtures = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_network_fixtures)
create_sqlite = _network_fixtures.create_sqlite

ZONE_IDS = ("10", "20", "30")
PUT_ONLY_ZONE = "2000115"
BIKE_ONLY_INTRAZONAL_ZONE = "50"
ONE_WAY_CONNECTOR_ZONE = "60"
SPLIT_REACHABILITY_ZONE = "15"
ISOLATED_ZONE = "55"
DEAD_CONNECTOR_ZONE = "40"


def default_demand_totals(
    zone_ids: tuple[str, ...] = ZONE_IDS,
    *,
    external_production: float = 1.0,
    external_attraction: float = 1.0,
    intrazonal: float = 0.0,
) -> dict[str, ZoneDemandTotals]:
    return {
        zone_id: ZoneDemandTotals(
            external_production=external_production,
            external_attraction=external_attraction,
            intrazonal=intrazonal,
        )
        for zone_id in zone_ids
    }


def create_demand_sqlite(
    path: str | Path,
    *,
    include_put_only_zone: bool = True,
    include_dead_connector_zone: bool = False,
    include_bike_only_intrazonal_zone: bool = False,
    include_one_way_connector_zone: bool = False,
    include_split_reachability_zone: bool = False,
) -> Path:
    """SQLite with network tables plus ZONE/CONNECTOR for demand tests."""
    path = Path(path)
    links = list(_network_fixtures.DEFAULT_LINKS) + [
        (800, 3, 4, "BIKE,CAR,HGV", 1, 1, 50.0),
        (800, 4, 3, "BIKE,CAR,HGV", 1, 1, 50.0),
    ]
    extra_nodes = {}
    extra_links = []
    if include_bike_only_intrazonal_zone or include_dead_connector_zone:
        extra_nodes[99] = (936000.0, 6267000.0)
        extra_links.extend(
            [
                (900, 3, 99, "BIKE", 1, 1, 15.0),
                (900, 99, 3, "BIKE", 1, 1, 15.0),
            ]
        )
    if include_split_reachability_zone:
        extra_nodes[6] = (936200.0, 6266200.0)
        extra_nodes[7] = (936300.0, 6266200.0)
        extra_links.extend(
            [
                (951, 1, 6, "CAR,HGV", 1, 1, 30.0),
                (960, 6, 7, "CAR,HGV", 1, 1, 20.0),
            ]
        )
    create_sqlite(path, links=links + extra_links, nodes={**_network_fixtures.DEFAULT_NODES, **extra_nodes})

    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE ZONE (NO INTEGER PRIMARY KEY, NAME TEXT)")
        for zone_id in ZONE_IDS:
            cur.execute(
                "INSERT INTO ZONE VALUES (?, ?)",
                (int(zone_id), f"zone_{zone_id}"),
            )
        if include_put_only_zone:
            cur.execute(
                "INSERT INTO ZONE VALUES (?, ?)",
                (int(PUT_ONLY_ZONE), "external_put_only"),
            )

        cur.execute(
            "CREATE TABLE CONNECTOR ("
            "ZONENO INTEGER, NODENO INTEGER, DIRECTION TEXT, TSYSSET TEXT, "
            '"WEIGHT(PRT)" INTEGER, TYPENO INTEGER)'
        )
        connectors = [
            (10, 1, "O", "BIKE,CAR,HGV,WALK", 50, 0),
            (10, 1, "D", "BIKE,CAR,HGV,WALK", 50, 0),
            (20, 2, "O", "BIKE,CAR,HGV,WALK", 50, 0),
            (20, 2, "D", "BIKE,CAR,HGV,WALK", 50, 0),
            (30, 3, "O", "BIKE,CAR,HGV,WALK", 50, 0),
            (30, 3, "D", "BIKE,CAR,HGV,WALK", 50, 0),
            (10, 2, "O", "BIKE,CAR,HGV,WALK", 0, 0),
        ]
        if include_put_only_zone:
            connectors.extend(
                [
                    (int(PUT_ONLY_ZONE), 4, "O", "PUTW", 100, 9),
                    (int(PUT_ONLY_ZONE), 4, "D", "PUTW", 100, 9),
                ]
            )
        if include_dead_connector_zone:
            connectors.extend(
                [
                    (int(DEAD_CONNECTOR_ZONE), 99, "O", "CAR", 100, 0),
                    (int(DEAD_CONNECTOR_ZONE), 99, "D", "CAR", 100, 0),
                ]
            )
            cur.execute(
                "INSERT INTO ZONE VALUES (?, ?)",
                (int(DEAD_CONNECTOR_ZONE), "dead_zone"),
            )
        if include_bike_only_intrazonal_zone:
            connectors.extend(
                [
                    (int(BIKE_ONLY_INTRAZONAL_ZONE), 99, "O", "BIKE,CAR", 100, 0),
                    (int(BIKE_ONLY_INTRAZONAL_ZONE), 99, "D", "BIKE,CAR", 100, 0),
                ]
            )
            cur.execute(
                "INSERT INTO ZONE VALUES (?, ?)",
                (int(BIKE_ONLY_INTRAZONAL_ZONE), "bike_only_intrazonal"),
            )
        if include_one_way_connector_zone:
            connectors.append(
                (int(ONE_WAY_CONNECTOR_ZONE), 3, "O", "BIKE,CAR,HGV,WALK", 50, 0),
            )
            cur.execute(
                "INSERT INTO ZONE VALUES (?, ?)",
                (int(ONE_WAY_CONNECTOR_ZONE), "one_way_connectors"),
            )
        if include_split_reachability_zone:
            connectors.extend(
                [
                    (10, 6, "O", "CAR,HGV", 100, 0),
                ]
            )
        cur.executemany(
            "INSERT INTO CONNECTOR VALUES (?, ?, ?, ?, ?, ?)",
            connectors,
        )
        conn.commit()
    finally:
        conn.close()
    return path


def create_isolated_zone_sqlite(path: str | Path) -> Path:
    """SQLite with a car zone on a subgraph disconnected from the main network."""
    path = Path(path)
    nodes = {
        **_network_fixtures.DEFAULT_NODES,
        6: (936200.0, 6266200.0),
        7: (936300.0, 6266200.0),
    }
    links = list(_network_fixtures.DEFAULT_LINKS) + [
        (961, 6, 7, "CAR,HGV", 1, 1, 20.0),
        (961, 7, 6, "CAR,HGV", 1, 1, 20.0),
        (800, 3, 4, "BIKE,CAR,HGV", 1, 1, 50.0),
        (800, 4, 3, "BIKE,CAR,HGV", 1, 1, 50.0),
    ]
    create_sqlite(path, links=links, nodes=nodes)

    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE ZONE (NO INTEGER PRIMARY KEY, NAME TEXT)")
        for zone_id in list(ZONE_IDS) + [ISOLATED_ZONE]:
            cur.execute(
                "INSERT INTO ZONE VALUES (?, ?)",
                (int(zone_id), f"zone_{zone_id}"),
            )
        cur.execute(
            "CREATE TABLE CONNECTOR ("
            "ZONENO INTEGER, NODENO INTEGER, DIRECTION TEXT, TSYSSET TEXT, "
            '"WEIGHT(PRT)" INTEGER, TYPENO INTEGER)'
        )
        connectors = [
            (10, 1, "O", "BIKE,CAR,HGV,WALK", 50, 0),
            (10, 1, "D", "BIKE,CAR,HGV,WALK", 50, 0),
            (20, 2, "O", "BIKE,CAR,HGV,WALK", 50, 0),
            (20, 2, "D", "BIKE,CAR,HGV,WALK", 50, 0),
            (30, 3, "O", "BIKE,CAR,HGV,WALK", 50, 0),
            (30, 3, "D", "BIKE,CAR,HGV,WALK", 50, 0),
            (int(ISOLATED_ZONE), 6, "O", "CAR,HGV", 100, 0),
            (int(ISOLATED_ZONE), 6, "D", "CAR,HGV", 100, 0),
        ]
        cur.executemany(
            "INSERT INTO CONNECTOR VALUES (?, ?, ?, ?, ?, ?)",
            connectors,
        )
        conn.commit()
    finally:
        conn.close()
    return path


def create_demand_omx(
    path: str | Path,
    *,
    include_put_core: bool = True,
    extra_zones: dict[str, dict[str, float]] | None = None,
) -> Path:
    path = Path(path)
    labels = list(ZONE_IDS)
    if extra_zones:
        labels.extend(extra_zones.keys())
    size = len(labels)
    if path.exists():
        path.unlink()
    with openmatrix.open_file(str(path), "w") as f:
        f.create_mapping("NO", labels)
        car = np.zeros((size, size))
        hvg = np.zeros((size, size))
        car[0, 1] = 10.0
        car[1, 2] = 2.0
        car[2, 2] = 3.0
        hvg[0, 1] = 1.0
        if extra_zones:
            for zone_id, cells in extra_zones.items():
                index = labels.index(zone_id)
                for other_id, value in cells.items():
                    other_index = labels.index(other_id)
                    car[index, other_index] = value
                    hvg[index, other_index] = value
        f["Car"] = car
        f["HVG"] = hvg
        if include_put_core:
            f["PUT"] = np.zeros((size, size))
    return path


def create_omx_missing_mapping(path: str | Path) -> Path:
    path = Path(path)
    if path.exists():
        path.unlink()
    with openmatrix.open_file(str(path), "w") as f:
        f["Car"] = np.array([[0.0, 1.0], [0.0, 0.0]])
    return path
