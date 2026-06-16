# Tasks — gis-api-mvp

## 1. Package scaffold

- [ ] 1.1 Create `tools/import/gis/` package layout per design.md (`api/`, `normalize/`, `omx/`, `orchestrate/`, `workspace/`)
- [ ] 1.2 Add `tests/tools/import/gis/` with TextTest stub and `README.md`
- [ ] 1.3 Add Python dependencies file for API (FastAPI, Uvicorn, geopandas, pyogrio, pyproj, openmatrix)

## 2. Workspace and job status

- [ ] 2.1 Implement `workspace/` module — scenario dirs, `status.json`, artifact paths (ADR-015)
- [ ] 2.2 Implement job state machine for build and run (`pending` → `building`/`running` → terminal states)

## 3. GIS normalization

- [ ] 3.1 Implement GeoJSON/GPKG reader with `?layer=` and default `zones` layer (ADR-011, ADR-014)
- [ ] 3.2 Implement CRS auto-detect, reproject, and transform logging (PRD §4)
- [ ] 3.3 Implement SQLite SpatiaLite read and `sqlite_joins` (ADR-013)
- [ ] 3.4 Export preprocessed layers for netconvert/polyconvert subprocess inputs

## 4. OMX adapter

- [ ] 4.1 Implement openmatrix reader → tazRelation XML writer (ADR-012)
- [ ] 4.2 Implement multi-slice interval mapping and vType from metadata
- [ ] 4.3 Validate OMX zone ids against normalized zones; fail loud on mismatch (ADR-014)

## 5. Scenario orchestration

- [ ] 5.1 Implement subprocess helpers using `sumolib.checkBinary` and config save pattern (ADR-006)
- [ ] 5.2 Wire netconvert + polyconvert build steps
- [ ] 5.3 Wire edgesInDistricts → tazs.xml from zones polygons
- [ ] 5.4 Wire od2trips + duarouter demand pipeline
- [ ] 5.5 Retain build logs and configs in workspace artifacts

## 6. HTTP API

- [ ] 6.1 Implement FastAPI app with ADR-010 routes and error shape (`specs/standards/api-standards.md`)
- [ ] 6.2 Implement multipart upload with 500 MB limit and asyncio background enqueue (ADR-008)
- [ ] 6.3 Implement artifact list/download and OpenAPI at `/v1/openapi.json`

## 7. Simulation

- [ ] 7.1 Implement sumocfg generation and subprocess sumo runner (ADR-015)
- [ ] 7.2 Implement `POST .../run` and `GET .../runs/{run_id}` endpoints

## 8. Packaging and tests

- [ ] 8.1 Add Dockerfile with SUMO binaries, GDAL, and API deps
- [ ] 8.2 Add minimal TextTest or pytest integration test for checkBinary + health endpoint
- [ ] 8.3 Add OMX fixture test: OMX → tazRelation → od2trips round-trip (ADR-012)

## 9. Spec hygiene

- [ ] 9.1 Update `specs/interfaces.md` OMX and HTTP rows to `partial` when implemented
- [ ] 9.2 Update `specs/coverage.md` when apply completes
- [ ] 9.3 Run `openspec validate gis-api-mvp`
