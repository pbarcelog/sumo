# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Unit tests for the VISUM SQLite network importer (import-network-sqlite).

Translation rules under test are normative in
``openspec/changes/import-network-sqlite/data-inventory.md``.
"""

from __future__ import annotations

import os
import shutil

import pytest

import sumolib

from gis.normalize.modes import map_tsysset
from gis.normalize.speed import resolve_edge_speed
from gis.normalize.visum_sqlite import (
    NetworkBuildOptions,
    VisumSQLiteError,
    normalize_sqlite_network,
)
from gis.normalize.visum_turns import read_turn_connections
from gis.orchestrate.netbuild import build_network_from_sqlite, write_plain_xml

from .fixtures import SPHERE_MERCATOR_WKT, create_sqlite, create_turn_sqlite


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


# --- 5.1 discovery -------------------------------------------------------

def test_discovery_reports_deferred_tables(tmp_path):
    db = create_sqlite(tmp_path / "ok.sqlite3", extra_tables=("STOP", "LINE", "LANETURN"))
    network = normalize_sqlite_network(db)
    assert {"STOP", "LINE", "LANETURN"}.issubset(set(network.deferred_tables))
    assert "TURN" not in network.deferred_tables


def test_discovery_missing_required_table_raises(tmp_path):
    db = create_sqlite(
        tmp_path / "missing.sqlite3",
        include_tables=("NETWORK", "NODE", "LINK", "TSYS"),  # no LINKTYPE
    )
    with pytest.raises(VisumSQLiteError, match="LINKTYPE"):
        normalize_sqlite_network(db)


# --- 5.2 direction -------------------------------------------------------

def test_bidirectional_creates_ab_and_reverse(tmp_path):
    db = create_sqlite(tmp_path / "dir.sqlite3")
    network = normalize_sqlite_network(db)
    edges = _edges_by_id(network)
    assert "100" in edges and "-100" in edges
    assert (edges["100"].from_node, edges["100"].to_node) == ("1", "2")
    assert (edges["-100"].from_node, edges["-100"].to_node) == ("2", "1")


def test_one_way_skips_empty_direction(tmp_path):
    db = create_sqlite(tmp_path / "oneway.sqlite3")
    network = normalize_sqlite_network(db)
    edges = _edges_by_id(network)
    assert "200" in edges
    assert "-200" not in edges
    assert "200:BA" in network.skipped_directions


def test_fully_closed_link_skipped(tmp_path):
    db = create_sqlite(tmp_path / "closed.sqlite3")
    network = normalize_sqlite_network(db)
    edges = _edges_by_id(network)
    assert "700" not in edges and "-700" not in edges
    assert "700:AB" in network.skipped_directions
    assert "700:BA" in network.skipped_directions


# --- 5.3 modes -----------------------------------------------------------

def test_mixed_mode_allows_passenger():
    vclasses, unmapped = map_tsysset("BIKE,CAR,HGV")
    assert set(vclasses) == {"bicycle", "passenger", "truck"}
    assert unmapped == []


def test_put_only_excludes_passenger(tmp_path):
    db = create_sqlite(tmp_path / "put.sqlite3")
    network = normalize_sqlite_network(db)
    edge = _edges_by_id(network)["300"]
    assert "passenger" not in edge.allow
    assert set(edge.allow) == {"bus", "rail_urban", "tram"}


def test_unmapped_token_reported(tmp_path):
    db = create_sqlite(tmp_path / "unmapped.sqlite3")
    network = normalize_sqlite_network(db)
    edge = _edges_by_id(network)["600"]
    assert "passenger" in edge.allow
    assert network.unmapped_tokens.get("FERRY") == 1


# --- 5.4 speed -----------------------------------------------------------

def test_put_only_positive_speed(tmp_path):
    db = create_sqlite(tmp_path / "putspeed.sqlite3")
    network = normalize_sqlite_network(db)
    edge = _edges_by_id(network)["300"]
    assert edge.speed_ms == pytest.approx(50 / 3.6)  # VDEF_PUTSYS, no epsilon


def test_restriction_for_each_slower_mode():
    linktype = {
        "VMAX_PRTSYS(CAR)": 50, "VMAX_PRTSYS(HGV)": 30,
        "VDEF_PUTSYS(BUS)": 45,
    }
    mapping = {"CAR": "passenger", "HGV": "truck", "BUS": "bus"}
    res = resolve_edge_speed(["passenger", "truck", "bus"], linktype, mapping)
    assert res.ceiling_kmh == pytest.approx(50)
    assert res.restrictions_kmh["truck"] == pytest.approx(30)
    assert res.restrictions_kmh["bus"] == pytest.approx(45)
    assert "passenger" not in res.restrictions_kmh  # mode at the ceiling


def test_low_ceiling_on_motorized_edge_flagged(tmp_path):
    db = create_sqlite(tmp_path / "coh.sqlite3")
    network = normalize_sqlite_network(db)
    assert any(w.startswith("500:") for w in network.coherence_warnings)


def test_low_ceiling_on_bike_only_not_flagged():
    linktype = {"VMAX_PRTSYS(BIKE)": 4}
    res = resolve_edge_speed(["bicycle"], linktype, {"BIKE": "bicycle"})
    assert res.coherence_warning is False


# --- 5.5 CRS -------------------------------------------------------------

def test_sphere_mercator_reprojected_and_logged(tmp_path):
    db = create_sqlite(tmp_path / "crs.sqlite3")
    network = normalize_sqlite_network(db)
    assert "Sphere_Mercator" in (network.source_wkt or "")
    assert network.target_epsg == "EPSG:25832"
    # Reprojected into UTM 32N range for Karlsruhe (~456 km E, ~5.43 Mm N).
    node = next(n for n in network.nodes if n.node_id == "1")
    assert 400000 < node.x < 520000
    assert 5300000 < node.y < 5500000


def test_missing_crs_raises(tmp_path):
    db = create_sqlite(tmp_path / "nocrs.sqlite3", projection=None)
    with pytest.raises(VisumSQLiteError, match="CRS"):
        normalize_sqlite_network(db)


def test_source_crs_override(tmp_path):
    db = create_sqlite(tmp_path / "override.sqlite3", projection=None)
    options = NetworkBuildOptions(source_crs=SPHERE_MERCATOR_WKT)
    network = normalize_sqlite_network(db, options)
    assert network.nodes  # builds without error using the override


# --- 5.6 geometry --------------------------------------------------------

def test_linkpoly_vertices_preserved_and_reversed(tmp_path):
    db = create_sqlite(tmp_path / "geom.sqlite3")
    network = normalize_sqlite_network(db)
    edges = _edges_by_id(network)
    ab = edges["100"].shape
    ba = edges["-100"].shape
    assert len(ab) == 4  # from-node + 2 vertices + to-node
    assert len(ba) == 4
    # BA is the AB shape reversed.
    assert ba == list(reversed(ab))


# --- 5.8 failures --------------------------------------------------------

def test_non_sqlite_input_raises(tmp_path):
    bogus = tmp_path / "bogus.sqlite3"
    bogus.write_text("this is not a database", encoding="utf-8")
    with pytest.raises(VisumSQLiteError):
        normalize_sqlite_network(bogus)


def test_missing_file_raises(tmp_path):
    with pytest.raises(VisumSQLiteError):
        normalize_sqlite_network(tmp_path / "does_not_exist.sqlite3")


def test_write_plain_xml_emits_files(tmp_path):
    db = create_sqlite(tmp_path / "xml.sqlite3")
    network = normalize_sqlite_network(db)
    out = tmp_path / "build"
    paths = write_plain_xml(network, out)
    assert paths["nod"].exists() and paths["edg"].exists() and paths["typ"].exists()
    edg = paths["edg"].read_text(encoding="utf-8")
    assert 'id="300"' in edg and "rail_urban" in edg
    typ = paths["typ"].read_text(encoding="utf-8")
    assert "restriction" in typ  # type 1 has slower bike/truck modes


def test_build_without_netconvert_stops_after_xml(tmp_path):
    db = create_sqlite(tmp_path / "noconv.sqlite3")
    result = build_network_from_sqlite(db, tmp_path / "out", run_netconvert=False)
    assert result.net_xml_path is None
    assert result.node_count == 4
    assert result.edge_count >= 5
    assert (tmp_path / "out" / "net.nod.xml").exists()


def test_turn_resolution_whitelist(tmp_path):
    db = create_turn_sqlite(tmp_path / "turns.sqlite3")
    network = normalize_sqlite_network(db)
    turns = read_turn_connections(db, network.edges)
    assert turns.turn_rows == 7
    assert turns.turn_rows_imported == 6
    assert turns.turn_rows_skipped == 1
    pairs = {(c.from_edge, c.to_edge) for c in turns.connections}
    assert ("100", "200") in pairs
    assert ("100", "400") in pairs
    assert ("100", "-100") not in pairs


def test_build_without_netconvert_reports_turn_stats(tmp_path):
    db = create_turn_sqlite(tmp_path / "turns.sqlite3")
    out = tmp_path / "out"
    result = build_network_from_sqlite(db, out, run_netconvert=False)
    assert result.turn_connection_count > 0
    assert result.turn_via_nodes == 1
    assert (out / "net.turn-allowed.con.xml").exists()
    assert not (out / "net.turn-patch.con.xml").exists()


# --- 5.7 build (requires netconvert) -------------------------------------

@needs_netconvert
def test_turn_junction_blocks_uturn(tmp_path):
    db = create_turn_sqlite(tmp_path / "turns.sqlite3")
    result = build_network_from_sqlite(db, tmp_path / "out")
    net = sumolib.net.readNet(str(result.net_xml_path))
    edge_100 = net.getEdge("100")
    outgoing_ids = {edge.getID() for edge in edge_100.getOutgoing().keys()}
    assert "200" in outgoing_ids
    assert "400" in outgoing_ids
    assert "-100" not in outgoing_ids


@needs_netconvert
def test_build_produces_loadable_net(tmp_path):
    db = create_sqlite(tmp_path / "build.sqlite3")
    result = build_network_from_sqlite(db, tmp_path / "out")
    assert result.net_xml_path is not None and result.net_xml_path.exists()
    net = sumolib.net.readNet(str(result.net_xml_path))
    speeds = [e.getSpeed() for e in net.getEdges()]
    assert all(s > 0 for s in speeds)  # zero zero-speed edges


# --- 6.x real Karlsruhe smoke (opt-in: requires the real DB) --------------

_REAL_DB = os.environ.get(
    "KARLSRUHE_SQLITE",
    os.path.join(os.path.expanduser("~"), "Downloads", "Karlsruhe", "Karlsruhe-sqlite.sqlite3"),
)
needs_real_db = pytest.mark.skipif(
    not os.path.isfile(_REAL_DB), reason="real Karlsruhe SQLite export not available"
)


@needs_real_db
def test_real_karlsruhe_normalization():
    network = normalize_sqlite_network(_REAL_DB)
    assert len(network.nodes) == 8432
    assert len(network.edges) == 19401
    assert len(network.skipped_directions) == 4089
    assert "Sphere_Mercator" in (network.source_wkt or "")
    assert network.target_epsg == "EPSG:25832"
    # The decisive invariant: no zero-speed edges, no fallback, no epsilon.
    assert not [e for e in network.edges if e.speed_ms <= 0]
    # Sampled PuT-only link disallows passenger.
    put = [e for e in network.edges if e.edge_id in ("3118", "-3118")]
    assert put and all("passenger" not in e.allow for e in put)


@needs_real_db
def test_real_karlsruhe_turn_import():
    network = normalize_sqlite_network(_REAL_DB)
    turns = read_turn_connections(_REAL_DB, network.edges)
    assert turns.turn_rows == 72812
    assert turns.turn_rows_skipped == 24619
    assert turns.turn_rows_imported == 48193
    assert len(turns.connections) > 35000
    assert len(turns.via_nodes) > 1000


@needs_netconvert
@needs_real_db
def test_real_karlsruhe_build_loads():
    import tempfile

    with tempfile.TemporaryDirectory() as out:
        result = build_network_from_sqlite(_REAL_DB, out)
        assert result.net_xml_path is not None and result.net_xml_path.exists()
        net = sumolib.net.readNet(str(result.net_xml_path))
        assert all(e.getSpeed() > 0 for e in net.getEdges())
