# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import os
import tempfile
from pathlib import Path

import pytest
import sumolib

from gis.orchestrate.assignment import AssignmentMethod, AssignmentOptions
from gis.orchestrate.scenario import RunnableScenarioOptions, build_runnable_scenario

_REAL_DB = os.environ.get("KARLSRUHE_SQLITE")
_REAL_OMX = os.environ.get("KARLSRUHE_OMX")
_REAL_NET = os.environ.get("KARLSRUHE_NET")


def _sumo_available() -> bool:
    try:
        sumolib.checkBinary("duarouter")
        sumolib.checkBinary("od2trips")
    except Exception:
        return False
    return True


needs_karlsruhe = pytest.mark.skipif(
    not _REAL_DB
    or not _REAL_OMX
    or not _REAL_NET
    or not os.path.isfile(_REAL_DB)
    or not os.path.isfile(_REAL_OMX)
    or not os.path.isfile(_REAL_NET)
    or not _sumo_available(),
    reason="Karlsruhe paths or SUMO binaries not available",
)


@pytest.mark.slow
@needs_karlsruhe
def test_karlsruhe_assignment_routes():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "karlsruhe"
        options = RunnableScenarioOptions(
            scenario_id="karlsruhe",
            assignment=AssignmentOptions(method=AssignmentMethod.DUAROUTER),
        )
        result = build_runnable_scenario(
            _REAL_OMX,
            _REAL_DB,
            _REAL_NET,
            workspace,
            options,
        )
        routes = result.layout.routes_xml
        assert routes.is_file()
        assert routes.stat().st_size > 0
