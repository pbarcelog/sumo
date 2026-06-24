# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import os
import sqlite3
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import openmatrix as omx
import pytest
import sumolib

from gis.normalize.demand_totals import zone_demand_totals_by_core
from gis.orchestrate.demand import DemandBuildOptions, build_demand_from_visum
from gis.orchestrate.netbuild import build_network_from_sqlite
from gis.orchestrate.reachable_trips import expected_trip_count, load_taz_relations

_REAL_DB = os.environ.get(
    "KARLSRUHE_SQLITE",
    os.path.join(os.path.expanduser("~"), "Downloads", "Karlsruhe", "Karlsruhe-sqlite.sqlite3"),
)
_REAL_OMX = os.environ.get(
    "KARLSRUHE_OMX",
    os.path.join(os.path.expanduser("~"), "Downloads", "Karlsruhe", "Visum_3_modes.omx"),
)
PUT_ONLY_ZONES = {str(zone_id) for zone_id in range(2000115, 2000143)}


def _sumo_available() -> bool:
    try:
        sumolib.checkBinary("od2trips")
        sumolib.checkBinary("netconvert")
    except Exception:
        return False
    return True


needs_real = pytest.mark.skipif(
    not os.path.isfile(_REAL_DB) or not os.path.isfile(_REAL_OMX) or not _sumo_available(),
    reason="Karlsruhe demand fixtures or SUMO binaries not available",
)


@needs_real
def test_real_karlsruhe_demand_smoke():
    """Full Karlsruhe OMX + SQLite + net.xml demand build (data-inventory §12)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        net = build_network_from_sqlite(_REAL_DB, tmp_path / "net").net_xml_path
        result = build_demand_from_visum(
            _REAL_OMX,
            _REAL_DB,
            net,
            tmp_path / "demand",
            DemandBuildOptions(run_duarouter=False),
        )

        conn = sqlite3.connect(_REAL_DB)
        zone_ids = {str(row[0]) for row in conn.execute("SELECT NO FROM ZONE")}
        conn.close()
        with omx.open_file(_REAL_OMX, "r") as f:
            omx_zones = {str(label) for label in f.mapping("NO").keys()}

        assert len(omx_zones) == 726
        assert omx_zones == zone_ids
        assert result.relation_counts["Car"] == 229_603
        assert result.relation_counts["HVG"] == 106_660
        assert PUT_ONLY_ZONES.issubset(set(result.excluded_zones["Car"]))
        assert "3951" in result.excluded_zones["Car"]

        passenger_taz_ids = {
            taz.get("id")
            for taz in ET.parse(result.tazs_paths["passenger"]).getroot().findall("taz")
        }
        totals = zone_demand_totals_by_core(_REAL_OMX, ("Car",))
        external_demand_zones = {
            zone_id
            for zone_id, zone_totals in totals["Car"].items()
            if zone_totals.has_external
        }
        assert external_demand_zones - set(result.excluded_zones["Car"]) <= passenger_taz_ids

        passenger_trips = result.trip_counts["passenger"]
        truck_trips = result.trip_counts["truck"]
        passenger_expected = expected_trip_count(load_taz_relations(result.taz_relation_paths["passenger"]))
        truck_expected = expected_trip_count(load_taz_relations(result.taz_relation_paths["truck"]))
        assert passenger_trips == passenger_expected
        assert truck_trips == truck_expected
        assert passenger_trips > 700_000
        assert truck_trips > 40_000
        assert any("3951" in message for message in result.messages)
