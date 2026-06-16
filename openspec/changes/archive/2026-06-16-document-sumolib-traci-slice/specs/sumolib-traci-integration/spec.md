# sumolib-traci-integration

Capability spec for sumolib orchestration helpers and simulation control options in the GIS API fork.

**ADR:** ADR-006, ADR-015
**PRD:** §3, §5

## ADDED Requirements

### Requirement: Binary resolution via sumolib.checkBinary

The orchestrator MUST resolve SUMO executables using `sumolib.checkBinary(name, bindir)` and honor `SUMO_HOME` / `<NAME>_BINARY` environment variables (`tools/sumolib/__init__.py:54–93`).

#### Scenario: CI without SUMO_HOME

- **WHEN** tests run with `SUMO_BINARY` set
- **THEN** `checkBinary` returns that path (see `tests/tools/sumolib/init/runner.py`)

### Requirement: Configuration template discovery

Orchestrators MUST support populating CLI options via `sumolib.options.pullOptions(executable, parser)` which reads `executable --save-template` (`options.py:88–90`).

#### Scenario: Dynamic netconvert options

- **WHEN** API exposes advanced netconvert flags
- **THEN** options match upstream binary template groups

### Requirement: XML artifact headers

Fork-generated SUMO XML MUST use `sumolib.xml.writeHeader` (or `writeXMLHeader` alias) for ADR-007 schema linkage.

#### Scenario: Additional file for edgeData

- **WHEN** orchestrator writes `<additional>` XML
- **THEN** header includes root element and XSD reference (osmWebWizard pattern)

### Requirement: Network inspection after build

The orchestrator MUST support `sumolib.net.readNet(path)` for validation, routing, or lon/lat conversion when `pyproj` and net geo-projection are available.

#### Scenario: Geo API response

- **WHEN** client requests coordinates in WGS84
- **THEN** `Net.convertXY2LonLat` is used on the scenario's `.net.xml`

### Requirement: Simulation run default (ADR-015)

Documentation MUST state that osmBuild and osmWebWizard run `sumo` via **subprocess** with `.sumocfg`, not TraCI. ADR-015 Accepted: v1 API uses subprocess Option A.

#### Scenario: MVP run without live control

- **WHEN** API runs simulation per ADR-015
- **THEN** orchestrator invokes `subprocess` with `sumo -c scenario.sumocfg` and collects XML outputs

### Requirement: TraCI documented as deferred control plane

TraCI (Option B) and libsumo/libtraci (Option D) are deferred to v2 per ADR-015. If adopted later, the API MUST use `traci.start([sumo, "-c", cfg])`, advance via `traci.simulationStep`, and close with `traci.close` (`traci/main.py`).

#### Scenario: Step-wise monitoring deferred

- **WHEN** v1 client requests simulation
- **THEN** subprocess path is used; TraCI live monitoring is not exposed

### Requirement: Libsumo environment switch documented

Agents MUST NOT assume libsumo unless `LIBSUMO_AS_TRACI` is set; default import is socket TraCI (`traci/__init__.py:41–59`).

#### Scenario: Headless API container

- **WHEN** evaluating in-process simulation for v2
- **THEN** libsumo multiprocessing limits per `docs/web/docs/Libsumo.md` are considered

### Requirement: Out-of-scope sumolib packages

GIS API orchestration MUST NOT depend on `sumolib.scenario`, `sumolib.visualization`, or `sumolib.output.convert` for MVP.

#### Scenario: Agent explores sumolib tree

- **WHEN** implementing build pipeline only
- **THEN** ADR-006 scope table is followed
