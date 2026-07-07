# Change: import-network-geojson

**Status:** Applied
**PRD:** §2 (formats), §4 (quality/CRS)
**ADRs:** 006 (orchestration), 009 (placement), 011 (normalization)
**Epic:** `gis-api-mvp` — Pillar 1 (network import), Phase 1.

## Why

`gis-api-mvp` was built breadth-first and was never validated against a real file. This change re-bases the first pillar — **network import** — as a small, **data-first** capability anchored to a real VISUM GeoJSON export (`node.geojson` + `link.geojson`, Karlsruhe). It produces a SUMO `net.xml` and is proven by importing the actual files, not synthetic stubs.

It also fixes a real translation problem found by inspecting the data: VISUM exports `V0PRT=0km/h` on 525 public-transport-only links (no `CAR` in `TSYSSET`). `V0PRT` is the *private-transport* free-flow speed, so 0 means "no private traffic", **not** "no PuT". A SUMO edge cannot have 0 speed, so these links must be translated into edges that **permit only their PuT vehicle classes** (`allow="bus tram rail ..."`, which inherently disallows `passenger`) — the consistent translation, avoiding any epsilon-speed hack.

## What Changes

- **ADD** `network-import` capability: read VISUM GeoJSON `node`/`link` → build SUMO `net.xml` via `netconvert`.
- **ADD** a **library-level entry point** (file paths in, `net.xml` + build report out). No HTTP in this change — the FastAPI surface wraps it later.
- **Import all links and nodes, no mode filtering.** PuT-only links are kept and modelled with `vClass` permissions (ADR-011 §normalization, team decision from data inspection).
- **Mode → vClass translation** from `TSYSSET` (`CAR→passenger`, `HGV→truck`, `BIKE→bicycle`, `BUS→bus`, `TRAM→tram`, `TRAIN→rail_urban`, `PUTW→pedestrian`); see `data-inventory.md`.
- **Directional split**: each VISUM link row yields an AB edge and a reverse edge from `R_*` fields; a direction with empty `TSYSSET` is omitted (one-way).
- **Speed rule**: edge speed = `V0PRT` (km/h→m/s) when `> 0`; otherwise a documented fallback by link class `LC` (PuT-only links). SQLite import (later change) may replace fallbacks with real PuT speeds.
- **CRS**: geometry is WGS84 (EPSG:4326); `netconvert` auto-projects to UTM (`--proj.utm`, EPSG:32632 for the Karlsruhe reference export). Resolved EPSG is logged (PRD §4, config CRS rule).
- **Control plan stand-in**: `netconvert --tls.guess` synthesises signals; real `CONTROLTYPE`-driven signal import is deferred to `import-control-plan`.

## Capabilities

### New Capabilities

- `network-import`: VISUM GeoJSON node/link discovery, field normalization, mode→vClass permission translation, CRS projection, directional split, `netconvert` build to `net.xml`, and build-report/log retention.

### Modified Capabilities

- *(none — no archived capabilities yet; `gis-api-mvp` becomes the umbrella epic.)*

## Impact

- **Code:** `tools/import/gis/normalize/**` (readers, CRS, translation) and `tools/import/gis/orchestrate/**` (netconvert build) — writable roots only (ADR-009). No HTTP, no `src/`/`tools/` edits.
- **Tests:** `tests/tools/import/gis/network/**` — synthetic fixtures + real-file smoke against `node.geojson`/`link.geojson`.
- **Specs:** `specs/interfaces.md` network/normalization rows move toward `partial`; `specs/coverage.md` notes Phase 1 start.
- **Anchor data:** `C:\Users\Pablo Barceló\Downloads\Karlsruhe\node.geojson`, `...\link.geojson`.
- **Dependencies:** geopandas, pyogrio, pyproj (already in API requirements); SUMO `netconvert`.

## Out of Scope

- SQLite source (`import-network-sqlite`), zones/TAZ, OD demand (`import-od-demand`), GTFS (`import-gtfs`).
- HTTP API surface, job orchestration, workspace status.
- Real signal-timing / control-plan import.
- PuT routing by timetable (handled in GTFS phase).
