# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Legacy OMX adapter tests (GeoJSON API path)."""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import openmatrix as omx

from gis.omx import validate_zone_ids, write_taz_relation


def test_legacy_write_taz_relation_and_validate():
    with tempfile.TemporaryDirectory() as tmp:
        omx_path = Path(tmp) / "demand.omx"
        out_path = Path(tmp) / "tazRelation.xml"
        with omx.open_file(str(omx_path), "w") as f:
            f.create_mapping("NO", ["1", "2"])
            f["matrix"] = np.array([[0.0, 10.0], [5.0, 0.0]])
        zones = write_taz_relation(omx_path, out_path, "DEFAULT_VEHTYPE")
        assert zones.zone_ids == {"1", "2"}
        validate_zone_ids(zones.zone_ids, {"1", "2"})
        tree = ET.parse(out_path)
        assert len(tree.findall(".//tazRelation")) == 2
