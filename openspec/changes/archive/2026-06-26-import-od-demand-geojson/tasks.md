# Tasks — import-od-demand-geojson

Data-first order (AequilibraE rhythm): inventory & fixtures **before** code; real-file smoke
**before** done. Do not check a box without evidence. Translation rules are normative in
`data-inventory.md`.

## 0. Review gate (blocking)

- [x] 0.1 Modeller signs off `data-inventory.md` §11: connector-from-GeoJSON only (no heuristics),
  centroid authority, OMX/PUT/weight rules aligned with `od-import-demand`.

## 1. Source inventory & fixtures

- [x] 1.1 Confirm field inventory in `data-inventory.md` against `zone_centroid.geojson`,
  `connector.geojson`, and OMX crosswalk §2.
- [x] 1.2 Add synthetic `zone_centroid.geojson` + `connector.geojson` fixtures (AB/`R_` expansion,
  CAR O+D, PuT-only zone, dead-node zone, empty TSYSSET skip).
- [x] 1.3 Add malformed connector GeoJSON fixture and OMX/zone misalignment fixture.
- [x] 1.4 Document expected Karlsruhe counts in `data-inventory.md` §10 (verify against real files).

## 2. GeoJSON zone/connector reader (`normalize/`)

- [x] 2.1 Read `zone_centroid.geojson` → zone id set (`NO`).
- [x] 2.2 Read `connector.geojson` → expand AB + `R_*` into `ConnectorRow` list; skip empty TSYSSET.
- [x] 2.3 Produce `ZoneConnectorTables` (same contract as `read_zone_connectors`).
- [x] 2.4 Fail loud on unreadable GeoJSON and missing zone ids on connector rows.

## 3. Refactor tazs build (`normalize/visum_zones.py`)

- [x] 3.1 Extract `build_tazs_for_core(tables, net, ...)` accepting `ZoneConnectorTables` directly.
- [x] 3.2 Keep `read_zone_connectors(sqlite)` as SQLite adapter calling shared expansion.

## 4. Demand orchestration (`orchestrate/demand.py`)

- [x] 4.1 Implement `build_demand_from_geojson(omx, zone_centroid, connector, net_xml, out_dir)`.
- [x] 4.2 Reuse OMX adapter, validation, reachable/od2trips stages from `build_demand_from_visum`.
- [x] 4.3 Return `DemandBuildResult` with paths, excluded zones, messages.

## 5. Unit tests (synthetic fixtures)

- [x] 5.1 `test_connector_expand` — AB/`R_` → 5,646-equivalent rows on Karlsruhe subset fixture.
- [x] 5.2 `test_omx_zone_align` — centroid ids match OMX mapping.
- [x] 5.3 `test_taz_resolve` — O→source, D→sink, vClass filter, uniform weights.
- [x] 5.4 `test_fail_loud` — malformed GeoJSON, misaligned OMX, dead-node external demand.
- [x] 5.5 `test_no_heuristic` — polygons absent from connector path (no edgesInDistricts call).

## 6. Real Karlsruhe smoke (opt-in, blocking for done)

- [x] 6.1 Build with real OMX + GeoJSON zones/connectors + `c:\tmp\karlsruhe-geojson-net\net.net.xml`.
- [x] 6.2 Assert expanded connectors == SQLite `CONNECTOR` (zero diffs on non-empty rows).
- [x] 6.3 Assert Car/HVG `tazs.xml` match SQLite-path output for same `net.xml`.
- [x] 6.4 Produce non-empty passenger trips (`reachable` or `od2trips`).
- [x] 6.5 Record results in `data-inventory.md` §12.

## 7. Spec hygiene & verification

- [x] 7.1 Update `specs/interfaces.md` — GeoJSON demand row.
- [x] 7.2 Update `specs/coverage.md` current focus.
- [x] 7.3 Run `pytest tests/tools/import/gis/demand/`.
- [x] 7.4 Run `openspec validate import-od-demand-geojson`.
