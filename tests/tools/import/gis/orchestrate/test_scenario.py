# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import importlib.util
import os
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import sumolib

from gis.orchestrate.assignment import AssignmentMethod, AssignmentOptions, AssignmentResult
from gis.orchestrate.netbuild import build_network_from_sqlite
from gis.orchestrate.scenario import RunnableScenarioOptions, build_runnable_scenario
from gis.workspace.manifest import RebuildPlan

_FIXTURES = importlib.util.spec_from_file_location(
    "demand_fixtures",
    Path(__file__).resolve().parent.parent / "demand" / "fixtures.py",
)
assert _FIXTURES and _FIXTURES.loader
fixtures = importlib.util.module_from_spec(_FIXTURES)
_FIXTURES.loader.exec_module(fixtures)
create_demand_omx = fixtures.create_demand_omx
create_demand_sqlite = fixtures.create_demand_sqlite


def _sumo_binary(name: str) -> bool:
    try:
        resolved = sumolib.checkBinary(name)
    except Exception:
        return False
    return shutil.which(resolved) is not None or os.path.isfile(resolved)


needs_od2trips = pytest.mark.skipif(
    not _sumo_binary("od2trips") or not _sumo_binary("netconvert"),
    reason="SUMO binaries not available",
)


def _mock_assignment_result(assignment_dir: Path) -> AssignmentResult:
    routes = assignment_dir / "routes.xml"
    routes.write_text(
        '<?xml version="1.0"?><routes><vehicle id="v0" depart="0"><route edges="e0"/></routes>',
        encoding="utf-8",
    )
    return AssignmentResult(
        routes_path=routes,
        log_path=assignment_dir / "duarouter.log",
        returncode=0,
        method=AssignmentMethod.DUAROUTER,
    )


@needs_od2trips
def test_build_runnable_scenario_produces_manifest_and_trips():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(tmp_path / "demand.sqlite3")
        omx = create_demand_omx(tmp_path / "demand.omx")
        net = build_network_from_sqlite(db, tmp_path / "netbuild").net_xml_path
        workspace = tmp_path / "workspace"
        options = RunnableScenarioOptions(
            assignment=AssignmentOptions(method=AssignmentMethod.DUAROUTER),
        )
        with mock.patch(
            "gis.orchestrate.scenario.run_assignment",
            side_effect=lambda **kwargs: _mock_assignment_result(kwargs["assignment_dir"]),
        ):
            result = build_runnable_scenario(omx, db, net, workspace, options)
        assert result.rebuild_plan == RebuildPlan.FULL
        assert (workspace / "demand" / "trips.passenger.xml").is_file()
        assert result.assignment is not None
        assert result.layout.manifest_path.is_file()
        assert result.sumocfg_path is not None


@needs_od2trips
def test_assignment_only_rebuild_reuses_trips():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = create_demand_sqlite(tmp_path / "demand.sqlite3")
        omx = create_demand_omx(tmp_path / "demand.omx")
        net = build_network_from_sqlite(db, tmp_path / "netbuild").net_xml_path
        workspace = tmp_path / "workspace"
        options = RunnableScenarioOptions(
            assignment=AssignmentOptions(method=AssignmentMethod.DUAROUTER),
        )
        with mock.patch(
            "gis.orchestrate.scenario.run_assignment",
            side_effect=lambda **kwargs: _mock_assignment_result(kwargs["assignment_dir"]),
        ):
            first = build_runnable_scenario(omx, db, net, workspace, options)
        trips_mtime = (workspace / "demand" / "trips.passenger.xml").stat().st_mtime

        net_copy = workspace / "network" / "net.net.xml"
        net_copy.write_bytes(net_copy.read_bytes() + b" ")

        with mock.patch(
            "gis.orchestrate.scenario.run_assignment",
            side_effect=lambda **kwargs: _mock_assignment_result(kwargs["assignment_dir"]),
        ) as run_assign:
            second = build_runnable_scenario(omx, db, net_copy, workspace, options)
        assert second.rebuild_plan == RebuildPlan.ASSIGNMENT_ONLY
        assert second.demand is None
        assert (workspace / "demand" / "trips.passenger.xml").stat().st_mtime == trips_mtime
        assert run_assign.called
