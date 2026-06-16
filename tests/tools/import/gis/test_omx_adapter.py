# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytest.importorskip("openmatrix")
import numpy as np
import openmatrix as omx

TOOLS_IMPORT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "tools", "import")
)
if TOOLS_IMPORT not in sys.path:
    sys.path.insert(0, TOOLS_IMPORT)

from gis.omx import validate_zone_ids, write_taz_relation


def _write_fixture_omx(path: Path) -> None:
    with omx.open_file(str(path), "w") as f:
        f.create_mapping("matrix", ["1", "2"])
        f["matrix"] = np.array([[0.0, 10.0], [5.0, 0.0]])


def test_write_taz_relation_and_validate():
    with tempfile.TemporaryDirectory() as tmp:
        omx_path = Path(tmp) / "demand.omx"
        out_path = Path(tmp) / "tazRelation.xml"
        _write_fixture_omx(omx_path)
        zones = write_taz_relation(omx_path, out_path)
        assert zones == {"1", "2"}
        validate_zone_ids(zones, {"1", "2"})
        tree = ET.parse(out_path)
        relations = tree.findall(".//tazRelation")
        assert len(relations) == 2


def test_validate_zone_ids_fails_loud():
    with pytest.raises(ValueError, match="strict match"):
        validate_zone_ids({"1", "2"}, {"1"})


@pytest.mark.skipif(
    not os.environ.get("SUMO_BINARY") and not os.environ.get("SUMO_HOME"),
    reason="SUMO not configured for od2trips round-trip",
)
def test_omx_to_od2trips_round_trip():
    """Integration: OMX → tazRelation when SUMO binaries are available."""
    import sumolib

    sumolib.checkBinary("od2trips")
    # Full round-trip requires net + tazs; covered in orchestration integration (future).
