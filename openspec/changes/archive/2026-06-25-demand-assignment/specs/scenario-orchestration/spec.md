# scenario-orchestration (delta)

Delta for `demand-assignment` change. Extends archived `scenario-orchestration` with VISUM demand path
and assignment defaults.

**PRD:** §2 (scenario build) | **ADR:** ADR-006

## MODIFIED Requirements

### Requirement: Target pipeline steps (API MVP)

The GIS API orchestrator MUST support the following ordered steps (implemented across `gis-api-mvp` and
`demand-assignment`):

1. GIS normalization (ADR-011) **or** VISUM SQLite network import (`import-network-sqlite`)
2. netconvert → `.net.xml` (GeoJSON path) **or** reuse SQLite-built `net.xml`
3. polyconvert → `.poly.xml` (when shapes/TAZ polygons provided — GeoJSON path only)
4. OMX adapter → `tazRelation.xml` (ADR-012) with VISUM `ZONE`/`CONNECTOR` → `tazs.xml` (ADR-014)
5. od2trips → per-vType `.trips.xml`
6. **Assignment** → `routes.xml` via `duaIterate.py` by default, or `duarouter` when explicitly selected
7. sumo run (optional, ADR-015)

Build manifests MUST record stage fingerprints so a `net.xml` revision can trigger assignment-only
rebuild when demand inputs are unchanged (`demand-assignment`).

#### Scenario: Network-only build

- **WHEN** client uploads spatial data without OMX
- **THEN** steps 4–6 are skipped; artifacts include network (and shapes if provided)

#### Scenario: Full scenario with OMX (GeoJSON path)

- **WHEN** client uploads spatial data and OMX matrix via the GeoJSON API path
- **THEN** all applicable GeoJSON-path steps execute; failures at any step abort with logged step name

#### Scenario: Full scenario with VISUM SQLite + OMX

- **WHEN** the VISUM library path is invoked with OMX, SQLite, and built `net.xml`
- **THEN** steps 4–6 execute under the reference workspace layout and produce `routes.xml` without
  manual assignment scripts

#### Scenario: Assignment defaults to duaIterate

- **WHEN** the orchestrator runs step 6 with default options on the VISUM path
- **THEN** `duaIterate.py` is used rather than a single-pass `duarouter` unless `assignment_method`
  overrides the default

## ADDED Requirements

### Requirement: Manifest-driven stage invalidation

The orchestrator MUST support rebuilding from a stored workspace manifest: unchanged OMX and SQLite with
a changed `net.xml` SHALL skip od2trips and re-run assignment only (v1 full route rebuild). PRD §4
(traceability); ADR-015.

#### Scenario: Assignment-only rebuild

- **WHEN** a workspace manifest shows matching OMX and SQLite hashes and a new `net.xml` hash
- **THEN** the orchestrator reuses `demand/trips.*` and re-executes assignment
