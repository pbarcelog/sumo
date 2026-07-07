# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Unit tests for the VISUM GeoJSON network importer (import-network-geojson).

Translation rules under test are normative in
``openspec/changes/import-network-geojson/data-inventory.md``.
"""

from __future__ import annotations

import os
import shutil
import tempfile

import pytest

import sumolib

from gis.normalize.modes import map_tsysset
from gis.normalize.speed import lc_fallback_kmh, parse_v0prt_kmh, resolve_geojson_edge_speed
from gis.normalize.visum_geojson import (
    GeoJsonBuildOptions,
    VisumGeoJsonError,
    normalize_geojson_network,
)
from gis.orchestrate.netbuild import build_network_from_geojson, write_geojson_plain_xml

from .geojson_fixtures import (
    create_geojson,
    write_malformed_link,
    write_missing_crs,
)


def _edges_by_id(network):
    return {e.edge_id: e for e in network.edges}


def _netconvert_available() -> bool:
    try:
        resolved = sumolib.checkBinary("netconvert")
    except Exception:
        return False
    return shutil.which(resolved) is not None or os.path.isfile(resolved)


needs_netconvert = pytest.mark.skipif(
    not _netconvert_available(), reason="netconvert binary not available in this environment"
)


# --- 5.1 modes -----------------------------------------------------------

def test_mixed_mode_allows_passenger():
    vclasses, unmapped = map_tsysset("BIKE,CAR,HGV")
    assert set(vclasses) == {"bicycle", "passenger", "truck"}
    assert unmapped == []


def test_put_only_excludes_passenger(tmp_path):
    nodes, links = create_geojson(tmp_path / "put")
    network = normalize_geojson_network(nodes, links)
    edge = _edges_by_id(network)["300"]
    assert "passenger" not in edge.allow
    assert set(edge.allow) == {"bus", "rail_urban", "tram"}


# --- 5.2 speed -----------------------------------------------------------

def test_v0prt_parsed_kmh():
    assert parse_v0prt_kmh("30km/h") == pytest.approx(30)
    assert parse_v0prt_kmh("0km/h") == pytest.approx(0)


def test_zero_v0prt_uses_lc_fallback_with_log():
    res = resolve_geojson_edge_speed("0km/h", "PuT", "3118")
    assert res.substituted is True
    assert res.speed_kmh == pytest.approx(50)
    assert res.speed_ms == pytest.approx(50 / 3.6)
    assert res.link_no == "3118"
    assert res.lc == "PuT"


def test_positive_v0prt_no_substitution():
    res = resolve_geojson_edge_speed("30km/h", "Collector", "100")
    assert res.substituted is False
    assert res.speed_kmh == pytest.approx(30)


def test_lc_fallback_major():
    assert lc_fallback_kmh("Major") == pytest.approx(70)


def test_put_only_positive_speed(tmp_path):
    nodes, links = create_geojson(tmp_path / "putspeed")
    network = normalize_geojson_network(nodes, links)
    edge = _edges_by_id(network)["300"]
    assert edge.speed_ms == pytest.approx(50 / 3.6)


# --- 5.3 direction -------------------------------------------------------

def test_bidirectional_creates_ab_and_reverse(tmp_path):
    nodes, links = create_geojson(tmp_path / "dir")
    network = normalize_geojson_network(nodes, links)
    edges = _edges_by_id(network)
    assert "100" in edges and "-100" in edges
    assert (edges["100"].from_node, edges["100"].to_node) == ("1", "2")
    assert (edges["-100"].from_node, edges["-100"].to_node) == ("2", "1")


def test_one_way_skips_empty_reverse(tmp_path):
    nodes, links = create_geojson(tmp_path / "oneway")
    network = normalize_geojson_network(nodes, links)
    edges = _edges_by_id(network)
    assert "200" in edges
    assert "-200" not in edges
    assert "200:BA" in network.skipped_directions


def test_fully_closed_link_skipped(tmp_path):
    nodes, links = create_geojson(tmp_path / "closed")
    network = normalize_geojson_network(nodes, links)
    edges = _edges_by_id(network)
    assert "700" not in edges and "-700" not in edges
    assert "700:AB" in network.skipped_directions
    assert "700:BA" in network.skipped_directions


# --- geometry / edge type ------------------------------------------------

def test_multi_vertex_geometry_preserved(tmp_path):
    nodes, links = create_geojson(tmp_path / "geom")
    network = normalize_geojson_network(nodes, links)
    edge = _edges_by_id(network)["500"]
    assert len(edge.shape) >= 3
    assert edge.type_id == "Major"


def test_lc_edge_type(tmp_path):
    nodes, links = create_geojson(tmp_path / "lc")
    network = normalize_geojson_network(nodes, links)
    assert _edges_by_id(network)["400"].type_id == "In-urban"


def test_unmapped_token_reported(tmp_path):
    nodes, links = create_geojson(tmp_path / "unmapped")
    network = normalize_geojson_network(nodes, links)
    assert network.unmapped_tokens.get("FERRY") == 2  # AB + BA directions


# --- 5.4 build -----------------------------------------------------------

def test_write_geojson_plain_xml_emits_files(tmp_path):
    nodes, links = create_geojson(tmp_path / "xml")
    network = normalize_geojson_network(nodes, links)
    paths = write_geojson_plain_xml(network, tmp_path / "build")
    assert paths["nod"].exists() and paths["edg"].exists()
    edg = paths["edg"].read_text(encoding="utf-8")
    assert 'id="300"' in edg and "rail_urban" in edg


def test_build_without_netconvert_stops_after_xml(tmp_path):
    nodes, links = create_geojson(tmp_path / "noconv")
    result = build_network_from_geojson(nodes, links, tmp_path / "out", run_netconvert=False)
    assert result.net_xml_path is None
    assert result.node_count == 4
    assert result.edge_count >= 5
    assert (tmp_path / "out" / "net.nod.xml").exists()


@needs_netconvert
def test_build_produces_loadable_net(tmp_path):
    nodes, links = create_geojson(tmp_path / "build")
    result = build_network_from_geojson(nodes, links, tmp_path / "out")
    assert result.net_xml_path is not None and result.net_xml_path.exists()
    net = sumolib.net.readNet(str(result.net_xml_path))
    speeds = [e.getSpeed() for e in net.getEdges()]
    assert all(s > 0 for s in speeds)
    put_edges = [e for e in net.getEdges() if e.getID() in ("300", "-300")]
    assert put_edges
    assert all(not e.allows("passenger") for e in put_edges)


# --- 5.5 failures --------------------------------------------------------

def test_malformed_link_raises(tmp_path):
    nodes, links = create_geojson(tmp_path / "ok")
    write_malformed_link(links)
    with pytest.raises(VisumGeoJsonError, match="Could not read GeoJSON"):
        normalize_geojson_network(nodes, links)


def test_missing_crs_uses_override(tmp_path):
    nodes, links = write_missing_crs(tmp_path / "nocrs")
    options = GeoJsonBuildOptions(source_crs="EPSG:4326")
    network = normalize_geojson_network(nodes, links, options)
    assert network.nodes


def test_missing_crs_without_override_raises(tmp_path):
    nodes, links = write_missing_crs(tmp_path / "nocrs2")
    options = GeoJsonBuildOptions(source_crs="")
    with pytest.raises(VisumGeoJsonError, match="CRS"):
        normalize_geojson_network(nodes, links, options)


def test_missing_file_raises(tmp_path):
    with pytest.raises(VisumGeoJsonError):
        normalize_geojson_network(tmp_path / "missing.geojson", tmp_path / "also.geojson")


# --- 6.x real Karlsruhe smoke (opt-in) -----------------------------------

_REAL_NODE = os.environ.get(
    "KARLSRUHE_NODE_GEOJSON",
    os.path.join(os.path.expanduser("~"), "Downloads", "Karlsruhe", "node.geojson"),
)
_REAL_LINK = os.environ.get(
    "KARLSRUHE_LINK_GEOJSON",
    os.path.join(os.path.expanduser("~"), "Downloads", "Karlsruhe", "link.geojson"),
)
needs_real_geojson = pytest.mark.skipif(
    not (os.path.isfile(_REAL_NODE) and os.path.isfile(_REAL_LINK)),
    reason="real Karlsruhe GeoJSON export not available",
)


@needs_real_geojson
def test_real_karlsruhe_normalization():
    network = normalize_geojson_network(_REAL_NODE, _REAL_LINK)
    assert len(network.nodes) == 8432
    assert len(network.edges) == 19401
    assert len(network.skipped_directions) == 4089
    assert network.target_epsg == "EPSG:4326"
    assert not [e for e in network.edges if e.speed_ms <= 0]
    put = [e for e in network.edges if e.edge_id in ("3118", "-3118")]
    assert put and all("passenger" not in e.allow for e in put)
    assert len(network.speed_substitutions) >= 525


@needs_netconvert
@needs_real_geojson
def test_real_karlsruhe_build_loads():
    with tempfile.TemporaryDirectory() as out:
        result = build_network_from_geojson(_REAL_NODE, _REAL_LINK, out)
        assert result.net_xml_path is not None and result.net_xml_path.exists()
        assert result.resolved_epsg is not None
        net = sumolib.net.readNet(str(result.net_xml_path))
        assert all(e.getSpeed() > 0 for e in net.getEdges())
        put = [e for e in net.getEdges() if e.getID() in ("3118", "-3118")]
        assert put and all(not e.allows("passenger") for e in put)
