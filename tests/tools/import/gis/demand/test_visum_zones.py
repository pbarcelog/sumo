# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import os
import shutil
import tempfile
from pathlib import Path

import pytest
import sumolib

from gis.normalize.demand_totals import ZoneDemandTotals
from gis.normalize.visum_zones import VisumZonesError, build_tazs_for_core
from gis.orchestrate.netbuild import build_network_from_sqlite

from .fixtures import (
    BIKE_ONLY_INTRAZONAL_ZONE,
    DEAD_CONNECTOR_ZONE,
    ONE_WAY_CONNECTOR_ZONE,
    PUT_ONLY_ZONE,
    ZONE_IDS,
    create_demand_sqlite,
    default_demand_totals,
)


def _netconvert_available() -> bool:
    try:
        resolved = sumolib.checkBinary("netconvert")
    except Exception:
        return False
    return shutil.which(resolved) is not None or os.path.isfile(resolved)


needs_netconvert = pytest.mark.skipif(
    not _netconvert_available(), reason="netconvert binary not available"
)


@needs_netconvert
def test_connector_resolve_origin_and_sink():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(tmp_path / "demand.sqlite3")
        net = build_network_from_sqlite(db, tmp_path / "build").net_xml_path
        result = build_tazs_for_core(
            db,
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


@needs_netconvert
def test_uniform_weights_and_zero_weight_connector_included():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(tmp_path / "demand.sqlite3")
        net = build_network_from_sqlite(db, tmp_path / "build").net_xml_path
        result = build_tazs_for_core(
            db,
            net,
            tmp_path / "tazs.passenger.xml",
            core="Car",
            vtype="passenger",
            demand_totals=default_demand_totals(),
            zero_demand_zone_ids=set(),
        )
        zone10 = next(record for record in result.records if record.taz_id == "10")
        assert len(zone10.sources) >= 2


@needs_netconvert
def test_put_only_zero_demand_zone_excluded():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(tmp_path / "demand.sqlite3")
        net = build_network_from_sqlite(db, tmp_path / "build").net_xml_path
        result = build_tazs_for_core(
            db,
            net,
            tmp_path / "tazs.passenger.xml",
            core="Car",
            vtype="passenger",
            demand_totals=default_demand_totals(),
            zero_demand_zone_ids={PUT_ONLY_ZONE},
        )
        assert PUT_ONLY_ZONE in result.excluded_zones
        assert PUT_ONLY_ZONE not in {record.taz_id for record in result.records}


@needs_netconvert
def test_fail_loud_when_external_demand_zone_has_no_edges():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(
            tmp_path / "demand.sqlite3",
            include_dead_connector_zone=True,
        )
        net = build_network_from_sqlite(db, tmp_path / "build").net_xml_path
        with pytest.raises(VisumZonesError, match="zone 40"):
            build_tazs_for_core(
                db,
                net,
                tmp_path / "tazs.passenger.xml",
                core="Car",
                vtype="passenger",
                demand_totals={
                    DEAD_CONNECTOR_ZONE: ZoneDemandTotals(external_production=5.0),
                },
                zero_demand_zone_ids=set(),
            )


@needs_netconvert
def test_intrazonal_only_zone_without_car_path_is_excluded():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(
            tmp_path / "demand.sqlite3",
            include_bike_only_intrazonal_zone=True,
        )
        net = build_network_from_sqlite(db, tmp_path / "build").net_xml_path
        result = build_tazs_for_core(
            db,
            net,
            tmp_path / "tazs.passenger.xml",
            core="Car",
            vtype="passenger",
            demand_totals={
                BIKE_ONLY_INTRAZONAL_ZONE: ZoneDemandTotals(intrazonal=4.0),
            },
            zero_demand_zone_ids=set(),
        )
        assert BIKE_ONLY_INTRAZONAL_ZONE in result.excluded_zones


@needs_netconvert
def test_synthesize_destination_connectors_from_all_origins():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(
            tmp_path / "demand.sqlite3",
            include_one_way_connector_zone=True,
        )
        net = build_network_from_sqlite(db, tmp_path / "build").net_xml_path
        result = build_tazs_for_core(
            db,
            net,
            tmp_path / "tazs.passenger.xml",
            core="Car",
            vtype="passenger",
            demand_totals={
                ONE_WAY_CONNECTOR_ZONE: ZoneDemandTotals(external_attraction=10.0),
            },
            zero_demand_zone_ids=set(),
        )
        zone60 = next(record for record in result.records if record.taz_id == ONE_WAY_CONNECTOR_ZONE)
        assert zone60.sources
        assert zone60.sinks
        assert any("synthesized" in message and ONE_WAY_CONNECTOR_ZONE in message for message in result.messages)


_KARLSRUHE_NET = os.environ.get(
    "KARLSRUHE_NET",
    r"c:\tmp\karlsruhe\network\net.net.xml",
)

needs_karlsruhe_net = pytest.mark.skipif(
    not os.path.isfile(_KARLSRUHE_NET),
    reason="Karlsruhe net.xml not available",
)


@needs_karlsruhe_net
def test_origin_connector_skips_dead_end_depart_edges():
    """Karlsruhe zone 1000018: -550081510 has no outgoing links and must not be a tazSource."""
    from gis.normalize.visum_zones import _incident_edge_ids

    net = sumolib.net.readNet(_KARLSRUHE_NET)
    sources = _incident_edge_ids(net, 105497759, "O", "passenger")
    assert "-550081510" not in sources
    assert "-550081505" in sources
