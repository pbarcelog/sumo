# Scenario Orchestration

Capability spec for Python orchestration of SUMO binaries in the GIS API fork (slice 1 brownfield).

**ADR:** ADR-006
**PRD:** §1, §5

## Requirements

### Requirement: Binary resolution via sumolib

The orchestrator MUST resolve SUMO binaries using `sumolib.checkBinary(name, bindir)` and honor `SUMO_HOME`.

#### Scenario: Missing SUMO_HOME

- **WHEN** `SUMO_HOME` is unset and binaries are not on PATH
- **THEN** the orchestrator fails with an explicit error before invoking subprocess

### Requirement: Configuration reproducibility

Each netconvert and polyconvert invocation MUST support saving configuration to `.netccfg` / `.polycfg` for audit and replay, following the `osmBuild.py` pattern.

#### Scenario: Replay from saved config

- **WHEN** a `.netccfg` exists from a prior build
- **THEN** `netconvert -c <cfg>` reproduces the same import options

### Requirement: Working directory discipline

Subprocess calls MUST use `cwd=output_directory` with relative paths where possible (`getRelative` pattern).

#### Scenario: Artifact isolation

- **WHEN** building scenario `abc123`
- **THEN** all outputs land under the scenario output directory without path leakage

### Requirement: Early validation

The orchestrator MUST validate inputs (files exist, output directory exists, required typemaps present) before long-running netconvert execution.

#### Scenario: Missing typemap

- **WHEN** polyconvert typemap is configured but file is missing
- **THEN** fail before netconvert completes (osmBuild early check pattern)

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

### Requirement: Manifest-driven stage invalidation

The orchestrator MUST support rebuilding from a stored workspace manifest: unchanged OMX and SQLite with
a changed `net.xml` SHALL skip od2trips and re-run assignment only (v1 full route rebuild). PRD §4
(traceability); ADR-015.

#### Scenario: Assignment-only rebuild

- **WHEN** a workspace manifest shows matching OMX and SQLite hashes and a new `net.xml` hash
- **THEN** the orchestrator reuses `demand/trips.*` and re-executes assignment

### Requirement: osmBuild as reference implementation

Documentation and new orchestration code MUST treat `tools/osmBuild.py` as the canonical reference for netconvert + polyconvert chaining (PRD §5).

#### Scenario: Developer onboarding

- **WHEN** an agent implements API orchestration
- **THEN** ADR-006 and this spec are consulted before writing subprocess code
