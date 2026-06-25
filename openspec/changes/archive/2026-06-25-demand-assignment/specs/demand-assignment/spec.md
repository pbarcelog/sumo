# demand-assignment

End-to-end VISUM demand build plus route assignment for runnable microsim scenarios (ADR-005, ADR-006,
ADR-009, ADR-015). Builds on archived `od-import-demand` (trips) and adds stage-2 assignment with a
stable reference workspace layout.

**PRD:** §1 (runnable scenarios), §2 (scenario build), §4 (determinism, fail-loud, traceability)
**Upstream:** [Assign tools](docs/web/docs/Tools/Assign.md), [Dynamic User Assignment](docs/web/docs/Demand/Dynamic_User_Assignment.md)

## ADDED Requirements

### Requirement: Orchestrate demand and assignment in one library entry point

The GIS API fork SHALL expose a library entry point that accepts OMX path, VISUM SQLite path, built
`net.xml`, workspace root, and build options, runs the `od-import-demand` pipeline to produce trip
files, then runs route assignment to produce `routes.xml`, returning paths, return codes, and a build
report. PRD §1 (runnable scenarios); ADR-006.

#### Scenario: End-to-end build produces routes

- **WHEN** valid OMX, SQLite, and `net.xml` are supplied and assignment is enabled (default)
- **THEN** the entry point writes demand artifacts under `demand/` and `routes.xml` under
  `assignment/`, and the build report records success with artifact paths

#### Scenario: Demand failure aborts before assignment

- **WHEN** `od2trips` exits non-zero for any vType
- **THEN** assignment is not invoked and the error references the failing log path

### Requirement: Default assignment uses dynamic user assignment

Assignment SHALL default to invoking upstream `duaIterate.py` (dynamic user assignment) with the built
`net.xml` and all per-vType trip files, saving logs and iteration outputs under `assignment/`. PRD §2
(scenario build); team decision (prefer `duaIterate` over static `duarouter` for v1).

#### Scenario: duaIterate is the default method

- **WHEN** assignment runs with default options
- **THEN** `duaIterate.py` is invoked (not bare `duarouter` alone) and the final `routes.xml` is
  copied or linked to `assignment/routes.xml`

#### Scenario: Configurable iteration count

- **WHEN** the caller sets `assignment_iterations` (e.g. `2`)
- **THEN** `duaIterate` receives the corresponding iteration flag and the manifest records the value

### Requirement: Single-pass duarouter remains available as opt-in

The orchestrator SHALL support `assignment_method=duarouter` as an explicit alternative to `duaIterate`
for fast or debug builds. PRD §2.

#### Scenario: Opt-in duarouter

- **WHEN** `assignment_method` is set to `duarouter`
- **THEN** `duarouter` is invoked once with the network and trip files and produces `routes.xml`

### Requirement: Pass multiple trip files with correct CLI semantics

When more than one vType trip file exists, the orchestrator SHALL pass them as a single comma-separated
`--trip-files` argument to `duarouter` and as a single comma-separated `-t` value to `duaIterate.py`.
It MUST NOT emit repeated `-t` flags (which upstream treats as overriding earlier inputs). PRD §4
(fail-loud); team decision (fix known wiring bug).

#### Scenario: Passenger and truck trips routed together

- **WHEN** `trips.passenger.xml` and `trips.truck.xml` exist
- **THEN** the assignment command includes
  `--trip-files trips.passenger.xml,trips.truck.xml` (duarouter) or
  `-t trips.passenger.xml,trips.truck.xml` (`duaIterate`) exactly once

### Requirement: Emit a reference workspace layout

The orchestrator SHALL write artifacts into a documented reference layout: `sources/` (optional input
copies or symlinks), `network/net.net.xml`, `demand/` (tazs, tazRelation, trips, od2trips logs),
`assignment/` (routes and assignment logs), and `sim/` (optional sumocfg). PRD §2 (artifact delivery);
ADR-015.

#### Scenario: Karlsruhe-compatible tree

- **WHEN** a workspace root is provided
- **THEN** outputs land under the subdirectories above and relative paths inside generated configs
  resolve within the workspace

### Requirement: Record a build manifest with content fingerprints

The orchestrator SHALL write `build-manifest.json` at the workspace root listing input paths, SHA-256
hashes of OMX, SQLite, and `net.xml`, per-stage artifact paths, assignment method, iteration count,
SUMO tool versions, and timestamps. PRD §4 (traceability).

#### Scenario: Manifest after successful build

- **WHEN** a build completes successfully
- **THEN** `build-manifest.json` exists and includes hashes for OMX, SQLite, and `net.xml`

### Requirement: Rebuild routes when the network revision changes

The orchestrator SHALL on a subsequent build against an existing workspace, when OMX and SQLite hashes
are unchanged but `net.xml` hash differs, reuse existing trip files and re-run assignment only (full
route rebuild). PRD §4 (determinism); team decision (v1 invalidation scope).

#### Scenario: Net-only change triggers assignment rebuild

- **WHEN** `build-manifest.json` exists, OMX and SQLite hashes match, and a new `net.xml` is supplied
- **THEN** `od2trips` is skipped, assignment runs again, and the manifest is updated with the new
  `net.xml` hash

#### Scenario: OMX or SQLite change triggers full demand rebuild

- **WHEN** OMX or SQLite hash differs from the stored manifest
- **THEN** demand artifacts and trips are regenerated before assignment

### Requirement: Provide a CLI entry point without per-scenario helper scripts

The fork SHALL expose a module CLI (e.g. `python -m gis.cli.build_scenario`) that accepts workspace and
input paths and invokes the library entry point, so operators do not maintain ad-hoc `PYTHONPATH` scripts
per scenario. PRD §1.

#### Scenario: CLI builds Karlsruhe workspace

- **WHEN** the CLI is run with OMX, SQLite, net, and workspace paths matching the Karlsruhe reference
- **THEN** it exits zero and `assignment/routes.xml` exists

### Requirement: Optionally emit a minimal sumocfg for GUI smoke

When `emit_sumocfg` is enabled, the orchestrator SHALL write `sim/<scenario_id>.sumocfg` referencing
`network/net.net.xml` and `assignment/routes.xml` with configurable begin, end, and
`time-to-teleport`. Simulation execution remains out of scope. PRD §2.

#### Scenario: sumocfg references built artifacts

- **WHEN** `emit_sumocfg=true` and the build succeeds
- **THEN** the sumocfg `net-file` and `route-files` point at the workspace-relative artifact paths

### Requirement: Validate Karlsruhe reference data end-to-end

The capability SHALL be verified against the real `Visum_3_modes.omx`, `Karlsruhe-sqlite.sqlite3`, and
`import-network-sqlite` `net.xml`, producing a non-empty `routes.xml`. Team decision (reference smoke
gate). Full-day demand volume and `sumo-gui` acceptance on the large Karlsruhe model are deferred
non-blocking until a smaller reference network exists (2026-06-25); a time-windowed subset (e.g. 1 h
`duaIterate`) satisfies this requirement for archive.

#### Scenario: Karlsruhe assignment smoke

- **WHEN** the real Karlsruhe inputs are processed with default assignment options (opt-in slow test)
- **THEN** `assignment/routes.xml` exists, is non-empty, and assignment logs report exit code zero
