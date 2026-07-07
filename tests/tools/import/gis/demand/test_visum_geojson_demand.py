# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Tests for GeoJSON zone/connector demand import (import-od-demand-geojson)."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import importlib.util

import openmatrix as omx
import pytest
import sumolib

from gis.normalize.visum_geojson_zones import read_zone_connectors_from_geojson
from gis.normalize.modes import split_tsysset
from gis.normalize.visum_zones import (
    VisumZonesError,
    build_tazs_for_core,
    build_tazs_for_core_from_tables,
    read_zone_connectors,
)
from gis.orchestrate.demand import DemandBuildOptions, build_demand_from_geojson
from gis.orchestrate.netbuild import build_network_from_geojson, build_network_from_sqlite

_network_geojson_path = Path(__file__).resolve().parent.parent / "network" / "geojson_fixtures.py"
_spec = importlib.util.spec_from_file_location("network_geojson_fixtures", _network_geojson_path)
assert _spec and _spec.loader
_network_geojson = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_network_geojson)
create_geojson = _network_geojson.create_geojson

from .fixtures import (
    DEAD_CONNECTOR_ZONE,
    ZONE_IDS,
    create_demand_omx,
    create_demand_sqlite,
    default_demand_totals,
)
from .geojson_fixtures import (
    create_demand_geojson,
    write_connector_unknown_zone,
    write_malformed_connector,
)


def _netconvert_available() -> bool:
    try:
        resolved = sumolib.checkBinary("netconvert")
    except Exception:
        return False
    return os.path.isfile(resolved) or __import__("shutil").which(resolved)


needs_netconvert = pytest.mark.skipif(
    not _netconvert_available(), reason="netconvert binary not available"
)


def _connector_row_set(connectors) -> set[tuple[str, str, str, str]]:
    return {
        (str(z), str(n), d, t or "")
        for z, n, d, t in connectors
        if split_tsysset(t)
    }


def test_connector_expand_matches_sqlite(tmp_path):
    db = create_demand_sqlite(tmp_path / "demand.sqlite3", include_one_way_connector_zone=True)
    zones, connectors = create_demand_geojson(
        tmp_path / "geojson",
        include_one_way_connector_zone=True,
    )
    geo_tables, skipped = read_zone_connectors_from_geojson(zones, connectors)
    sql_tables = read_zone_connectors(db)
    assert _connector_row_set(geo_tables.connectors) == _connector_row_set(sql_tables.connectors)
    assert geo_tables.zone_ids == sql_tables.zone_ids
    assert all("empty-TSYSSET" in item for item in skipped)


def test_omx_zone_aligns_with_centroids(tmp_path):
    omx_path = create_demand_omx(tmp_path / "demand.omx")
    zones, connectors = create_demand_geojson(
        tmp_path / "geojson",
        include_put_only_zone=False,
    )
    geo_tables, _ = read_zone_connectors_from_geojson(zones, connectors)
    with omx.open_file(str(omx_path), "r") as f:
        omx_zones = {str(label) for label in f.mapping("NO").keys()}
    assert omx_zones == geo_tables.zone_ids == set(ZONE_IDS)


@needs_netconvert
def test_taz_resolve_origin_and_sink(tmp_path):
    db = create_demand_sqlite(tmp_path / "demand.sqlite3")
    zones, connectors = create_demand_geojson(tmp_path / "geojson")
    net = build_network_from_sqlite(db, tmp_path / "netbuild").net_xml_path
    geo_tables, _ = read_zone_connectors_from_geojson(zones, connectors)
    result = build_tazs_for_core_from_tables(
        geo_tables,
        net,
        tmp_path / "tazs.passenger.xml",
        core="Car",
        vtype="passenger",
        demand_totals=default_demand_totals(),
        zero_demand_zone_ids=set(),
    )
    zone10 = next(record for record in result.records if record.taz_id == "10")
    assert "100" in zone10.sources
    assert "-100" in zone10.sinks
    text = (tmp_path / "tazs.passenger.xml").read_text(encoding="utf-8")
    assert 'weight="1"' in text


def test_malformed_connector_raises(tmp_path):
    zones, connectors = create_demand_geojson(tmp_path / "geojson")
    write_malformed_connector(connectors)
    with pytest.raises(VisumZonesError, match="Could not read GeoJSON"):
        read_zone_connectors_from_geojson(zones, connectors)


def test_unknown_connector_zone_raises(tmp_path):
    zones, connectors = write_connector_unknown_zone(tmp_path / "bad")
    with pytest.raises(VisumZonesError, match="unknown zone"):
        read_zone_connectors_from_geojson(zones, connectors)


@needs_netconvert
def test_dead_connector_external_demand_raises(tmp_path):
    db = create_demand_sqlite(
        tmp_path / "demand.sqlite3",
        include_dead_connector_zone=True,
    )
    zones, connectors = create_demand_geojson(
        tmp_path / "geojson",
        include_dead_connector_zone=True,
    )
    net = build_network_from_sqlite(db, tmp_path / "netbuild").net_xml_path
    geo_tables, _ = read_zone_connectors_from_geojson(zones, connectors)
    totals = default_demand_totals(zone_ids=(*ZONE_IDS, DEAD_CONNECTOR_ZONE))
    with pytest.raises(VisumZonesError, match="no resolvable tazSource"):
        build_tazs_for_core_from_tables(
            geo_tables,
            net,
            tmp_path / "tazs.passenger.xml",
            core="Car",
            vtype="passenger",
            demand_totals=totals,
            zero_demand_zone_ids=set(),
        )


def test_no_edges_in_districts_heuristic():
    import gis.normalize.visum_geojson_zones as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "edgesInDistricts" not in source


@needs_netconvert
def test_build_demand_from_geojson_produces_trips(tmp_path):
    db = create_demand_sqlite(tmp_path / "demand.sqlite3")
    omx = create_demand_omx(tmp_path / "demand.omx")
    nodes, links = create_geojson(tmp_path / "net_geojson")
    net = build_network_from_geojson(nodes, links, tmp_path / "netbuild").net_xml_path
    zones, connectors = create_demand_geojson(tmp_path / "demand_geojson")
    result = build_demand_from_geojson(
        omx,
        zones,
        connectors,
        net,
        tmp_path / "demand_out",
        DemandBuildOptions(run_duarouter=False),
    )
    assert result.trip_counts["passenger"] > 0
    assert result.trips_paths["passenger"].exists()


_REAL_DB = os.environ.get(
    "KARLSRUHE_SQLITE",
    os.path.join(os.path.expanduser("~"), "Downloads", "Karlsruhe", "Karlsruhe-sqlite.sqlite3"),
)
_REAL_OMX = os.environ.get(
    "KARLSRUHE_OMX",
    os.path.join(os.path.expanduser("~"), "Downloads", "Karlsruhe", "Visum_3_modes.omx"),
)
_REAL_ZONE = os.environ.get(
    "KARLSRUHE_ZONE_GEOJSON",
    os.path.join(os.path.expanduser("~"), "Downloads", "Karlsruhe", "zone_centroid.geojson"),
)
_REAL_CONNECTOR = os.environ.get(
    "KARLSRUHE_CONNECTOR_GEOJSON",
    os.path.join(os.path.expanduser("~"), "Downloads", "Karlsruhe", "connector.geojson"),
)
_REAL_NET = os.environ.get(
    "KARLSRUHE_GEOJSON_NET",
    r"c:\tmp\karlsruhe-geojson-net\net.net.xml",
)
needs_real = pytest.mark.skipif(
    not all(os.path.isfile(p) for p in (_REAL_DB, _REAL_OMX, _REAL_ZONE, _REAL_CONNECTOR, _REAL_NET))
    or not _netconvert_available(),
    reason="Karlsruhe GeoJSON demand fixtures or net.xml not available",
)


@needs_real
def test_real_karlsruhe_geojson_connectors_match_sqlite():
    geo_tables, _ = read_zone_connectors_from_geojson(_REAL_ZONE, _REAL_CONNECTOR)
    sql_tables = read_zone_connectors(_REAL_DB)
    assert len(geo_tables.connectors) == 5640  # 5646 sqlite rows minus 6 empty TSYSSET
    assert _connector_row_set(geo_tables.connectors) == _connector_row_set(sql_tables.connectors)


@needs_real
def test_real_karlsruhe_geojson_demand_smoke():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        opts = DemandBuildOptions(run_duarouter=False)
        geo_result = build_demand_from_geojson(
            _REAL_OMX,
            _REAL_ZONE,
            _REAL_CONNECTOR,
            _REAL_NET,
            tmp_path / "geojson_demand",
            opts,
        )
        sql_result = __import__(
            "gis.orchestrate.demand", fromlist=["build_demand_from_visum"]
        ).build_demand_from_visum(
            _REAL_OMX,
            _REAL_DB,
            _REAL_NET,
            tmp_path / "sqlite_demand",
            opts,
        )
        assert geo_result.tazs_paths["passenger"].read_bytes() == (
            sql_result.tazs_paths["passenger"].read_bytes()
        )
        assert geo_result.tazs_paths["truck"].read_bytes() == (
            sql_result.tazs_paths["truck"].read_bytes()
        )
        assert geo_result.trip_counts["passenger"] > 700_000
        assert geo_result.trip_counts["truck"] > 40_000

        conn = sqlite3.connect(_REAL_DB)
        sql_count = conn.execute("SELECT COUNT(*) FROM CONNECTOR").fetchone()[0]
        conn.close()
        assert sql_count == 5646
