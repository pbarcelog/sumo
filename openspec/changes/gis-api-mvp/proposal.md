# Change: gis-api-mvp

**Status:** Proposed
**PRD:** §2, §3, §6
**ADRs:** 008–015 (Accepted 2026-06-16)

## Why

Tier B workshop decisions are recorded. Context extraction is complete. The fork needs a first implementation pass that delivers the PRD §6 end-to-end path: accept GeoJSON/GPKG/SQLite + OMX, build a SUMO scenario via existing binaries, and optionally run `sumo` — all from new code under `tools/import/gis/**` without modifying upstream SUMO.

## What Changes

- **ADD** FastAPI HTTP service (`tools/import/gis/api/`) per ADR-008/010.
- **ADD** GIS normalization (`tools/import/gis/normalize/`) — geopandas/pyogrio, CRS logging (ADR-011).
- **ADD** OMX → tazRelation adapter (`tools/import/gis/omx/`) (ADR-012).
- **ADD** Scenario build orchestrator (`tools/import/gis/orchestrate/`) — netconvert, polyconvert, edgesInDistricts, od2trips, duarouter (ADR-006, ADR-014).
- **ADD** Subprocess simulation runner with local filesystem workspace (ADR-015).
- **ADD** Docker packaging scaffold and TextTest stubs under `tests/tools/import/gis/`.
- **ADD** OpenAPI 3.x document for `/v1/scenarios` contract.
- **NO** edits to existing `src/` or `tools/` files (read-only upstream).

## Capabilities

### New Capabilities

- `gis-api-http`: REST endpoints, multipart upload, job status, artifact download (ADR-010).
- `gis-normalization`: GeoJSON/GPKG/SQLite → preprocess artifacts for netconvert/polyconvert (ADR-011, ADR-013).
- `omx-adapter`: OMX → tazRelation XML via openmatrix (ADR-012).
- `scenario-orchestration`: Full build pipeline from normalized inputs to routes (ADR-006, ADR-014).
- `scenario-simulation`: Subprocess `sumo` execution and run outputs (ADR-015).

### Modified Capabilities

- *(none — `openspec/specs/` has no archived capabilities yet)*

## Impact

- **Code:** `tools/import/gis/**`, `tests/tools/import/gis/**` only.
- **Specs:** `specs/interfaces.md` HTTP/OMX rows move from `gap` to `partial` on apply.
- **Dependencies:** FastAPI, Uvicorn, geopandas, pyogrio, pyproj, openmatrix (API container).
- **Deployment:** Docker image with SUMO binaries + GDAL + Python stack.
