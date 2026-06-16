# scenario-simulation

Subprocess SUMO simulation execution (ADR-015).

**PRD:** §3 journey 4

## ADDED Requirements

### Requirement: Run sumo via subprocess

The simulation runner SHALL invoke `sumo -c scenario.sumocfg` via subprocess using `sumolib.checkBinary('sumo')`. ADR-015 Option A.

#### Scenario: Successful run

- **WHEN** client triggers run on ready scenario
- **THEN** subprocess completes and run status becomes `completed`

### Requirement: Local filesystem run workspace

Each run SHALL write outputs under `{workspace}/scenarios/{scenario_id}/runs/{run_id}/`. ADR-015.

#### Scenario: Output paths

- **WHEN** simulation completes
- **THEN** run directory contains `tripinfos.xml` and `summary.xml` per sumocfg outputs

### Requirement: Generate sumocfg

The runner SHALL generate `.sumocfg` referencing built network and routes before invoking sumo, following osmWebWizard pattern. ADR-006.

#### Scenario: Config references artifacts

- **WHEN** run starts
- **THEN** sumocfg references `net.xml` and route files from build workspace

### Requirement: Poll run status

The API SHALL expose run state via `GET /v1/scenarios/{id}/runs/{run_id}` with states `pending`, `running`, `completed`, `failed`. ADR-010.

#### Scenario: Run in progress

- **WHEN** sumo subprocess is active
- **THEN** run status returns `running`
