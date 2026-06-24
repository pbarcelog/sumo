# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import sumolib

from gis.normalize.visum_zones import VisumZonesError
from gis.omx.adapter import write_taz_relation_for_core, OmxAdapterOptions
from gis.orchestrate.demand import DemandBuildOptions, build_demand_from_visum
from gis.orchestrate.netbuild import build_network_from_sqlite
from gis.orchestrate.reachable_trips import (
    expected_trip_count,
    load_taz_relations,
    verify_trips_routable,
    write_reachable_trips,
)
from gis.normalize.visum_zones import build_tazs_for_core

from .fixtures import (
    ZONE_IDS,
    create_demand_omx,
    create_demand_sqlite,
    create_isolated_zone_sqlite,
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
def test_reachable_trips_all_pairs_routable():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(tmp_path / "demand.sqlite3")
        omx = create_demand_omx(tmp_path / "demand.omx")
        net = build_network_from_sqlite(db, tmp_path / "netbuild").net_xml_path
        result = build_demand_from_visum(
            omx,
            db,
            net,
            tmp_path / "demand_out",
            DemandBuildOptions(run_duarouter=False, trip_generation="reachable"),
        )
        assert result.trip_counts["passenger"] > 0
        assert verify_trips_routable(net, result.trips_paths["passenger"]) == 0
        assert verify_trips_routable(net, result.trips_paths["truck"]) == 0


@needs_netconvert
def test_reachable_trips_fail_loud_on_disconnected_od_pair():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_isolated_zone_sqlite(tmp_path / "demand.sqlite3")
        omx = create_demand_omx(
            tmp_path / "demand.omx",
            extra_zones={"55": {"20": 5.0}},
        )
        net = build_network_from_sqlite(db, tmp_path / "netbuild").net_xml_path
        with pytest.raises(VisumZonesError, match="55->20"):
            build_demand_from_visum(
                omx,
                db,
                net,
                tmp_path / "demand_out",
                DemandBuildOptions(run_duarouter=False, trip_generation="reachable"),
            )


@needs_netconvert
def test_reachable_trips_skips_unreachable_connector_draw():
    """Zone with two sources: one on an isolated spur cannot absorb O-D demand alone."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(tmp_path / "demand.sqlite3", include_split_reachability_zone=True)
        omx = create_demand_omx(tmp_path / "demand.omx")
        net = build_network_from_sqlite(db, tmp_path / "netbuild").net_xml_path
        out = tmp_path / "demand_out"
        tazs = out / "tazs.passenger.xml"
        taz_rel = out / "tazRelation.passenger.xml"
        out.mkdir(parents=True)
        taz_result = build_tazs_for_core(
            db,
            net,
            tazs,
            core="Car",
            vtype="passenger",
            demand_totals=default_demand_totals(),
            zero_demand_zone_ids=set(),
        )
        write_taz_relation_for_core(
            omx,
            taz_rel,
            "Car",
            OmxAdapterOptions(),
            zone_access=taz_result.zone_access,
        )
        trips = out / "trips.passenger.xml"
        write_reachable_trips(net, tazs, taz_rel, trips, vtype="passenger", prefix="passenger", seed=1)
        assert verify_trips_routable(net, trips) == 0
        tree = ET.parse(trips)
        from_edges = {trip.get("from") for trip in tree.findall("trip")}
        assert "-100" in from_edges or "-200" in from_edges
        assert "960" not in from_edges
