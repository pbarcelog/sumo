# Change: import-od-demand-geojson

**Status:** Applied (2026-06-26)
**PRD:** §1 (OMX + spatial → runnable demand), §2 (formats), §4 (fail-loud, traceability)
**ADRs:** 005 (OD pipeline), 006 (orchestration), 009 (placement), 012 (OMX), 014 (TAZ)
**Epic:** `gis-api-mvp` — Pillar 2 (demand), federated GeoJSON path.
**Depends on:** `network-import` (GeoJSON `net.xml`; ids preserved). **Companion:** `data-inventory.md`.

## Why

`import-network-geojson` delivers a Karlsruhe `net.xml` from `node.geojson` + `link.geojson`, but
microsimulation still needs **TAZ definitions** (`tazs.xml`) and an **OD matrix** (`tazRelation.xml`).
The SQLite demand path (`od-import-demand`) already proves OMX + `CONNECTOR` → `tazs` on Karlsruhe;
the federated export also ships **`zone_centroid.geojson`**, **`connector.geojson`**, and
`Visum_3_modes.omx`. Measured crosswalk: non-empty expanded `connector.geojson` rows **match SQLite
`CONNECTOR` exactly** on `(ZONENO,NODENO,DIRECTION,TSYSSET)` — **5,640** GeoJSON rows vs **5,646**
SQLite rows (6 SQLite rows with empty `TSYSSET` omitted in the GeoJSON export) — and OMX `NO` labels
match zone centroids (726/726). This change closes the demand gap for the **GeoJSON-first** workflow
without polygon heuristics or SQLite.

## What Changes

- **ADD** `od-import-demand-geojson` capability: OMX + GeoJSON zones/connectors → `tazRelation.xml` +
  `tazs.xml`, then orchestrate trip generation (`reachable` or `od2trips`).
- **Read zones** from `zone_centroid.geojson` (`NO` = TAZ id); polygons optional/diagnostic only in v1.
- **Read connectors** from `connector.geojson`: expand AB + `R_*` (BA) rows into directed
  `(ZONENO, NODENO, DIRECTION, TSYSSET)` records — same semantics as SQLite `CONNECTOR`.
- **Reuse** OMX adapter (`omx/adapter.py`), zone→edge resolution (`visum_zones.py` core logic), and
  mode mapping (`modes.py`) — new GeoJSON reader feeds the existing `ZoneConnectorTables` contract.
- **Library entry point:** `build_demand_from_geojson(omx, zone_centroid, connector, net_xml, out_dir)`.
- **Explicitly out of scope (stage 2):** heuristic connector generation (AequilibraE k-nearest /
  polygon inference); `edgesInDistricts` polygon fallback; PUT road-loading.

## Capabilities

### New Capabilities

- `od-import-demand-geojson`: GeoJSON zone centroid + connector discovery, AB/`R_` directional
  expansion, OMX → `tazRelation`, connector → `tazs.xml`, strict OMX↔zone alignment, fail-loud rules,
  and demand orchestration on top of a GeoJSON-built `net.xml`.

### Modified Capabilities

- *(none — SQLite `od-import-demand` requirements unchanged; this is a sibling federated source path.)*

## Impact

- **Code:** `tools/import/gis/normalize/` (GeoJSON zone/connector reader), refactor
  `visum_zones.py` to accept `ZoneConnectorTables` from any source; `orchestrate/demand.py` (new
  entry point). Writable roots only (ADR-009).
- **Tests:** `tests/tools/import/gis/demand/` — GeoJSON fixtures + Karlsruhe opt-in smoke comparing
  `tazs.xml` parity with SQLite path for Car/HVG.
- **Specs:** `specs/interfaces.md`; optional ADR-014 note for GeoJSON connector export (Option E
  equivalent).
- **Anchor data:** `Visum_3_modes.omx`, `zone_centroid.geojson`, `connector.geojson`, GeoJSON
  `net.xml` (`c:\tmp\karlsruhe-geojson-net\net.net.xml`).

## Out of Scope

- Heuristic connector synthesis from polygons/centroids (AequilibraE second process — next stage).
- `zone_polygon.geojson` → `edgesInDistricts` fallback (ADR-014 Option A).
- PUT core trip generation (same deferral as SQLite path).
- HTTP API, scenario manifest changes (follow-on).
