# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import openmatrix as omx
import pytest

from gis.omx import OmxAdapterOptions, validate_zone_alignment, validate_zone_ids, write_taz_relation
from gis.omx.adapter import write_taz_relation_for_core

from .fixtures import BIKE_ONLY_INTRAZONAL_ZONE, ZONE_IDS, create_demand_omx, create_omx_missing_mapping


def test_omx_mapping_uses_no_labels():
    with tempfile.TemporaryDirectory() as tmp:
        omx_path = Path(tmp) / "demand.omx"
        create_demand_omx(omx_path)
        out_path = Path(tmp) / "tazRelation.xml"
        result = write_taz_relation(
            omx_path,
            out_path,
            OmxAdapterOptions(cores=("Car", "HVG"), skip_cores=("PUT",)),
        )
        assert result.zone_ids == set(ZONE_IDS)
        tree = ET.parse(out_path)
        from_ids = {element.get("from") for element in tree.findall(".//tazRelation")}
        assert "0" not in from_ids
        assert "10" in from_ids
        intervals = tree.findall(".//interval")
        assert {element.get("id") for element in intervals} == {"passenger", "truck"}


def test_missing_mapping_fails_loud():
    with tempfile.TemporaryDirectory() as tmp:
        omx_path = Path(tmp) / "bad.omx"
        create_omx_missing_mapping(omx_path)
        with pytest.raises(ValueError, match="no mapping"):
            write_taz_relation(
                omx_path,
                Path(tmp) / "out.xml",
                OmxAdapterOptions(cores=("Car",), skip_cores=()),
            )


def test_intervals_skip_zeros_keep_intrazonal():
    with tempfile.TemporaryDirectory() as tmp:
        omx_path = Path(tmp) / "demand.omx"
        create_demand_omx(omx_path)
        out_path = Path(tmp) / "car.xml"
        write_taz_relation_for_core(omx_path, out_path, "Car")
        relations = ET.parse(out_path).findall(".//tazRelation")
        assert len(relations) == 3
        assert any(element.get("from") == element.get("to") == "30" for element in relations)


def test_put_core_skipped_with_report():
    with tempfile.TemporaryDirectory() as tmp:
        omx_path = Path(tmp) / "demand.omx"
        create_demand_omx(omx_path)
        result = write_taz_relation(
            omx_path,
            Path(tmp) / "all.xml",
            OmxAdapterOptions(),
        )
        assert "PUT" in result.skipped_cores


def test_intrazonal_dropped_when_zone_has_no_spawn_absorb_path():
    with tempfile.TemporaryDirectory() as tmp:
        omx_path = Path(tmp) / "demand.omx"
        create_demand_omx(
            omx_path,
            extra_zones={BIKE_ONLY_INTRAZONAL_ZONE: {BIKE_ONLY_INTRAZONAL_ZONE: 5.0}},
        )
        out_path = Path(tmp) / "car.xml"
        zone_access = {
            zone_id: (True, True) for zone_id in ZONE_IDS
        }
        zone_access[BIKE_ONLY_INTRAZONAL_ZONE] = (False, False)
        result = write_taz_relation_for_core(
            omx_path,
            out_path,
            "Car",
            zone_access=zone_access,
        )
        relations = ET.parse(out_path).findall(".//tazRelation")
        assert not any(
            element.get("from") == element.get("to") == BIKE_ONLY_INTRAZONAL_ZONE
            for element in relations
        )
        assert any(BIKE_ONLY_INTRAZONAL_ZONE in message for message in result.messages)


def test_validate_zone_alignment_fails_on_unknown_omx_zone():
    with pytest.raises(ValueError, match="absent from ZONE"):
        validate_zone_alignment({"999"}, {"10", "20"}, {"10", "20"})


def test_legacy_write_taz_relation_still_works():
    with tempfile.TemporaryDirectory() as tmp:
        omx_path = Path(tmp) / "legacy.omx"
        out_path = Path(tmp) / "tazRelation.xml"
        with omx.open_file(str(omx_path), "w") as f:
            f.create_mapping("NO", ["1", "2"])
            f["matrix"] = np.array([[0.0, 10.0], [5.0, 0.0]])
        zones = write_taz_relation(omx_path, out_path, "DEFAULT_VEHTYPE")
        assert zones.zone_ids == {"1", "2"}
        validate_zone_ids(zones.zone_ids, {"1", "2"})


def test_validate_zone_ids_fails_loud():
    with pytest.raises(ValueError, match="strict match"):
        validate_zone_ids({"1", "2"}, {"1"})
