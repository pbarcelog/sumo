# gis-api-http

HTTP REST surface for scenario build and simulation (ADR-008, ADR-010).

**PRD:** §3

## ADDED Requirements

### Requirement: Create scenario build job

The API SHALL expose `POST /v1/scenarios` accepting `multipart/form-data` uploads and optional JSON `build_options`, returning HTTP `202` with a UUID `scenario_id`. PRD §3 journey 1.

#### Scenario: Multipart upload accepted

- **WHEN** client posts spatial files and OMX within 500 MB per file
- **THEN** API returns `scenario_id` and enqueues background build

#### Scenario: Upload exceeds limit

- **WHEN** any uploaded file exceeds 500 MB
- **THEN** API returns HTTP `413` with error shape per `specs/standards/api-standards.md`

### Requirement: Poll build status

The API SHALL expose `GET /v1/scenarios/{id}/status` returning `state`, `step`, `progress`, and `error` when failed. PRD §3 journey 2.

#### Scenario: Build in progress

- **WHEN** background build is running
- **THEN** status response includes `state` of `building` and current `step`

### Requirement: List and download artifacts

The API SHALL expose `GET /v1/scenarios/{id}/artifacts` listing build outputs and support `?name=` for single file download. PRD §3 journey 3.

#### Scenario: Build complete

- **WHEN** build reaches `ready` state
- **THEN** artifacts list includes at minimum `net.xml` when network build succeeded

### Requirement: Start simulation run

The API SHALL expose `POST /v1/scenarios/{id}/run` and `GET /v1/scenarios/{id}/runs/{run_id}` per ADR-015. PRD §3 journey 4.

#### Scenario: Run enqueued

- **WHEN** client posts run on a `ready` scenario
- **THEN** API returns `run_id` and subprocess sumo is scheduled in background

### Requirement: GPKG layer selection

The API SHALL honor `?layer=<name>` for GPKG uploads per ADR-010.

#### Scenario: Layer override

- **WHEN** client uploads GPKG with `?layer=roads`
- **THEN** normalization reads the named layer not the default

### Requirement: OpenAPI document

The API SHALL serve OpenAPI 3.x at `/v1/openapi.json` describing all v1 routes. ADR-010.

#### Scenario: Schema available

- **WHEN** client requests `/v1/openapi.json`
- **THEN** response validates as OpenAPI 3.x and lists `/v1/scenarios` paths
