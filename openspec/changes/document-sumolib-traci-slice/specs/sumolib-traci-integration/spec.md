# sumolib / TraCI Integration

Capability spec for sumolib orchestration helpers and simulation control options in the GIS API fork.

**Change:** document-sumolib-traci-slice
**ADR:** ADR-006, ADR-015
**PRD:** §3, §5

---

## Requirements

### Requirement: Binary resolution via sumolib.checkBinary

The orchestrator MUST resolve SUMO executables using `sumolib.checkBinary(name, bindir)` and honor `SUMO_HOME` / `<NAME>_BINARY` environment variables (`tools/sumolib/__init__.py:54–93`).

#### Scenario: CI without SUMO_HOME

- **WHEN** tests run with `SUMO_BINARY` set
- **THEN** `checkBinary` returns that path (see `tests/tools/sumolib/init/runner.py`)

---

### Requirement: Configuration template discovery

Orchestrators MAY populate CLI options via `sumolib.options.pullOptions(executable, parser)` which reads `executable --save-template` (`options.py:88–90`).

#### Scenario: Dynamic netconvert options

- **WHEN** API exposes advanced netconvert flags
- **THEN** options match upstream binary template groups

---

### Requirement: XML artifact headers

Fork-generated SUMO XML MUST use `sumolib.xml.writeHeader` (or `writeXMLHeader` alias) for ADR-007 schema linkage.

#### Scenario: Additional file for edgeData

- **WHEN** orchestrator writes `<additional>` XML
- **THEN** header includes root element and XSD reference (osmWebWizard pattern)

---

### Requirement: Network inspection after build

The orchestrator MAY call `sumolib.net.readNet(path)` for validation, routing, or lon/lat conversion when `pyproj` and net geo-projection are available.

#### Scenario: Geo API response

- **WHEN** client requests coordinates in WGS84
- **THEN** `Net.convertXY2LonLat` is used on the scenario's `.net.xml`

---

### Requirement: Simulation run default (ADR-015 pending)

Documentation MUST state that osmBuild and osmWebWizard run `sumo` via **subprocess** with `.sumocfg`, not TraCI.

#### Scenario: MVP run without live control

- **WHEN** ADR-015 Option A is selected
- **THEN** API invokes `subprocess` with `sumo -c scenario.sumocfg` and collects XML outputs

---

### Requirement: TraCI documented as optional control plane

If ADR-015 selects TraCI (Option B), the API MUST use `traci.start([sumo, "-c", cfg])` or equivalent, advance via `traci.simulationStep`, and close with `traci.close` (`traci/main.py`).

#### Scenario: Step-wise monitoring

- **WHEN** client requests live vehicle counts during run
- **THEN** TraCI `vehicle` and `simulation` domains are consulted (workshop defines API surface)

---

### Requirement: Libsumo environment switch documented

Agents MUST NOT assume libsumo unless `LIBSUMO_AS_TRACI` is set; default import is socket TraCI (`traci/__init__.py:41–59`).

#### Scenario: Headless API container

- **WHEN** evaluating in-process simulation
- **THEN** workshop considers libsumo multiprocessing limits per `docs/web/docs/Libsumo.md`

---

### Requirement: Out-of-scope sumolib packages

GIS API orchestration MUST NOT depend on `sumolib.scenario`, `sumolib.visualization`, or `sumolib.output.convert` for MVP.

#### Scenario: Agent explores sumolib tree

- **WHEN** implementing build pipeline only
- **THEN** ADR-006 scope table is followed
