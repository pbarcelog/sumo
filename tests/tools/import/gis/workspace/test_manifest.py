# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import json
import tempfile
from pathlib import Path

from gis.workspace.manifest import (
    AssignmentFingerprint,
    BuildManifest,
    InputFingerprints,
    RebuildPlan,
    build_manifest,
    load_manifest,
    plan_rebuild,
    save_manifest,
    sha256_file,
)


def test_sha256_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "data.bin"
        path.write_bytes(b"karlsruhe")
        digest = sha256_file(path)
        assert len(digest) == 64
        assert digest == sha256_file(path)


def test_manifest_save_load():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "build-manifest.json"
        manifest = BuildManifest(
            created_at="2026-01-01T00:00:00+00:00",
            sumo_version="test",
            inputs=InputFingerprints(omx="a", sqlite="b", net_xml="c"),
            assignment=AssignmentFingerprint(
                method="duarouter", iterations=2, begin=0, end=7200
            ),
            artifacts={"routes_xml": "assignment/routes.xml"},
        )
        save_manifest(path, manifest)
        loaded = load_manifest(path)
        assert loaded is not None
        assert loaded.inputs is not None
        assert loaded.inputs.omx == "a"
        assert loaded.assignment is not None
        assert loaded.assignment.method == "duarouter"


def test_plan_rebuild_net_only():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        omx = tmp_path / "a.omx"
        sqlite = tmp_path / "b.sqlite3"
        net = tmp_path / "net.xml"
        omx.write_bytes(b"omx")
        sqlite.write_bytes(b"sql")
        net.write_bytes(b"net-v1")

        manifest = build_manifest(
            omx=omx,
            sqlite=sqlite,
            net_xml=net,
            assignment_method="duarouter",
            assignment_iterations=2,
            assignment_begin=0,
            assignment_end=7200,
            artifacts={},
        )
        net.write_bytes(b"net-v2")
        plan = plan_rebuild(
            manifest,
            omx=omx,
            sqlite=sqlite,
            net_xml=net,
            assignment_method="duarouter",
            assignment_iterations=2,
            assignment_begin=0,
            assignment_end=7200,
            trips_exist=True,
            routes_exist=True,
        )
        assert plan == RebuildPlan.ASSIGNMENT_ONLY


def test_plan_rebuild_omx_change():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        omx = tmp_path / "a.omx"
        sqlite = tmp_path / "b.sqlite3"
        net = tmp_path / "net.xml"
        omx.write_bytes(b"omx-v1")
        sqlite.write_bytes(b"sql")
        net.write_bytes(b"net")
        manifest = build_manifest(
            omx=omx,
            sqlite=sqlite,
            net_xml=net,
            assignment_method="duarouter",
            assignment_iterations=2,
            assignment_begin=0,
            assignment_end=7200,
            artifacts={},
        )
        omx.write_bytes(b"omx-v2")
        plan = plan_rebuild(
            manifest,
            omx=omx,
            sqlite=sqlite,
            net_xml=net,
            assignment_method="duarouter",
            assignment_iterations=2,
            assignment_begin=0,
            assignment_end=7200,
            trips_exist=True,
            routes_exist=True,
        )
        assert plan == RebuildPlan.FULL
