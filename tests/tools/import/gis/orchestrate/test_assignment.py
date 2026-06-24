# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import tempfile
from pathlib import Path
from unittest import mock

import pytest

from gis.orchestrate.assignment import AssignmentMethod, AssignmentOptions, run_assignment


def test_duarouter_argv_uses_comma_trip_files():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        assignment = tmp_path / "assignment"
        assignment.mkdir()
        demand = tmp_path / "demand"
        demand.mkdir()
        net = tmp_path / "net.net.xml"
        net.write_text("<net/>", encoding="utf-8")
        vtypes = tmp_path / "vtypes.add.xml"
        vtypes.write_text("<additional/>", encoding="utf-8")
        trips = {
            "passenger": demand / "trips.passenger.xml",
            "truck": demand / "trips.truck.xml",
        }
        for path in trips.values():
            path.write_text("<routes/>", encoding="utf-8")

        with mock.patch("gis.orchestrate.assignment.save_and_run", return_value=0) as save:
            run_assignment(
                net_xml=net,
                trip_paths=trips,
                assignment_dir=assignment,
                vtypes_xml=vtypes,
                options=AssignmentOptions(method=AssignmentMethod.DUAROUTER),
            )
            args = save.call_args[0][1]
            assert args.count("--trip-files") == 1
            idx = args.index("--trip-files")
            assert "trips.passenger.xml" in args[idx + 1]
            assert "trips.truck.xml" in args[idx + 1]
            assert "-t" not in args
