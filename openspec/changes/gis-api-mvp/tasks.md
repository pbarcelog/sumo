# Tasks — gis-api-mvp

## 1. Package scaffold

- [x] 1.1 Create `tools/import/gis/` package layout per design.md (`api/`, `normalize/`, `omx/`, `orchestrate/`, `workspace/`)
- [x] 1.2 Add `tests/tools/import/gis/` with TextTest stub and `README.md`
- [x] 1.3 Add Python dependencies file for API (FastAPI, Uvicorn, geopandas, pyogrio, pyproj, openmatrix)

## 2. Workspace and job status

- [x] 2.1 Implement `workspace/` module — scenario dirs, `status.json`, artifact paths (ADR-015)
- [x] 2.2 Implement job state machine for build and run (`pending` → `building`/`running` → terminal states)

## 3. GIS normalization

- [x] 3.1 Implement GeoJSON/GPKG reader with `?layer=` and default `zones` layer (ADR-011, ADR-014)
- [x] 3.2 Implement CRS auto-detect, reproject, and transform logging (PRD §4)
- [x] 3.3 Implement SQLite SpatiaLite read and `sqlite_joins` (ADR-013)
- [x] 3.4 Export preprocessed layers for netconvert/polyconvert subprocess inputs

## 4. OMX adapter

- [x] 4.1 Implement openmatrix reader → tazRelation XML writer (ADR-012)
- [x] 4.2 Implement multi-slice interval mapping and vType from metadata
- [x] 4.3 Validate OMX zone ids against normalized zones; fail loud on mismatch (ADR-014)

## 5. Scenario orchestration

- [x] 5.1 Implement subprocess helpers using `sumolib.checkBinary` and config save pattern (ADR-006)
- [x] 5.2 Wire netconvert + polyconvert build steps
- [x] 5.3 Wire edgesInDistricts → tazs.xml from zones polygons
- [x] 5.4 Wire od2trips + duarouter demand pipeline
- [x] 5.5 Retain build logs and configs in workspace artifacts

## 6. HTTP API

- [x] 6.1 Implement FastAPI app with ADR-010 routes and error shape (`specs/standards/api-standards.md`)
- [x] 6.2 Implement multipart upload with 500 MB limit and asyncio background enqueue (ADR-008)
- [x] 6.3 Implement artifact list/download and OpenAPI at `/v1/openapi.json`

## 7. Simulation

- [x] 7.1 Implement sumocfg generation and subprocess sumo runner (ADR-015)
- [x] 7.2 Implement `POST .../run` and `GET .../runs/{run_id}` endpoints

## 8. Packaging and tests

- [x] 8.1 Add Dockerfile with SUMO binaries, GDAL, and API deps
- [x] 8.2 Add minimal TextTest or pytest integration test for checkBinary + health endpoint
- [x] 8.3 Add OMX fixture test: OMX → tazRelation → od2trips round-trip (ADR-012)

## 9. Spec hygiene

- [x] 9.1 Update `specs/interfaces.md` OMX and HTTP rows to `partial` when implemented
- [x] 9.2 Update `specs/coverage.md` when apply completes
- [x] 9.3 Run `openspec validate gis-api-mvp`
