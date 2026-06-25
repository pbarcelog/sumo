# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import tempfile
from pathlib import Path
from unittest import mock

import pytest

from gis.orchestrate.assignment import (
    AssignmentMethod,
    AssignmentOptions,
    _resolve_dua_iterate_route,
    _stage_trips_for_dua_iterate,
    run_assignment,
)


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
            assert "--additional-files" in args


def test_stage_trips_for_dua_iterate_embeds_vtype_once():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        vtypes = tmp_path / "vtypes.add.xml"
        vtypes.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<additional>
    <vType id="passenger" vClass="passenger"/>
</additional>""",
            encoding="utf-8",
        )
        trips = tmp_path / "trips.passenger.xml"
        trips.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<routes>
    <trip id="t0" depart="0" from="e0" to="e1" type="passenger"/>
</routes>""",
            encoding="utf-8",
        )
        staged = _stage_trips_for_dua_iterate(
            {"passenger": trips},
            vtypes,
            tmp_path / "staging",
        )
        text = staged["passenger"].read_text(encoding="utf-8")
        assert text.count('<vType id="passenger"') == 1
        assert 'id="t0"' in text


def test_resolve_dua_iterate_route_prefers_gz():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        step_dir = tmp_path / "000"
        step_dir.mkdir()
        gz = step_dir / "trips.passenger.dua_000.rou.xml.gz"
        gz.write_bytes(b"unused")
        resolved = _resolve_dua_iterate_route(step_dir, "trips.passenger.dua", 0)
        assert resolved == gz


def test_dua_iterate_argv_omits_duarouter_additional_files():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        assignment = tmp_path / "assignment"
        assignment.mkdir()
        demand = tmp_path / "demand"
        demand.mkdir()
        net = tmp_path / "net.net.xml"
        net.write_text("<net/>", encoding="utf-8")
        vtypes = tmp_path / "vtypes.add.xml"
        vtypes.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<additional><vType id="passenger" vClass="passenger"/></additional>""",
            encoding="utf-8",
        )
        trips = {
            "passenger": demand / "trips.passenger.xml",
        }
        trips["passenger"].write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<routes><trip id="t0" depart="0" from="e0" to="e1" type="passenger"/></routes>""",
            encoding="utf-8",
        )

        with mock.patch("gis.orchestrate.assignment.run_python_tool", return_value=0) as run_tool:
            with mock.patch(
                "gis.orchestrate.assignment.resolve_tool_script",
                return_value=str(tmp_path / "duaIterate.py"),
            ):
                with mock.patch("gis.orchestrate.assignment._dua_iterate_output_routes", return_value=[]):
                    with mock.patch("gis.orchestrate.assignment._merge_route_files"):
                        (tmp_path / "duaIterate.py").write_text("", encoding="utf-8")
                        run_assignment(
                            net_xml=net,
                            trip_paths=trips,
                            assignment_dir=assignment,
                            vtypes_xml=vtypes,
                            options=AssignmentOptions(
                                method=AssignmentMethod.DUAITERATE,
                                iterations=2,
                            ),
                        )
            args = run_tool.call_args[0][1]
            assert not any(arg.startswith("duarouter--additional-files") for arg in args)
            assert (assignment / "staging" / "trips.passenger.dua.xml").is_file()
