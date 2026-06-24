# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import os
import shutil
import tempfile
from pathlib import Path

import pytest
import sumolib

from gis.orchestrate.demand import DemandBuildOptions, build_demand_from_visum
from gis.orchestrate.netbuild import build_network_from_sqlite

from .fixtures import create_demand_omx, create_demand_sqlite


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
def test_build_demand_from_visum_produces_trips():
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
            DemandBuildOptions(run_duarouter=False),
        )
        assert result.trip_counts["passenger"] > 0
        assert result.trips_paths["truck"].exists()
        assert result.trips_paths["passenger"].read_text(encoding="utf-8").strip()
        assert "PUT" in result.skipped_cores


@needs_netconvert
def test_taz_artifacts_are_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(tmp_path / "demand.sqlite3")
        omx = create_demand_omx(tmp_path / "demand.omx")
        net = build_network_from_sqlite(db, tmp_path / "netbuild").net_xml_path
        opts = DemandBuildOptions(run_od2trips=False)
        first = build_demand_from_visum(omx, db, net, tmp_path / "run1", opts)
        second = build_demand_from_visum(omx, db, net, tmp_path / "run2", opts)
        assert first.tazs_paths["passenger"].read_bytes() == second.tazs_paths["passenger"].read_bytes()
        assert first.taz_relation_paths["passenger"].read_bytes() == (
            second.taz_relation_paths["passenger"].read_bytes()
        )
