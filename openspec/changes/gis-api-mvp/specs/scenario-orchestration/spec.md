# scenario-orchestration

Scenario build pipeline invoking SUMO binaries (ADR-006, ADR-014).

**PRD:** §2, §3

## ADDED Requirements

### Requirement: Resolve binaries via sumolib

The orchestrator SHALL resolve all SUMO executables via `sumolib.checkBinary` honoring `SUMO_HOME` and `*_BINARY` environment variables. ADR-006.

#### Scenario: netconvert resolution

- **WHEN** build step requires netconvert
- **THEN** orchestrator invokes resolved absolute path from checkBinary

### Requirement: Execute build sequence

The orchestrator SHALL run netconvert, polyconvert, edgesInDistricts (for TAZ), od2trips, and duarouter in dependency order per `specs/interfaces.md` target API sequence. ADR-006.

#### Scenario: Full demand pipeline

- **WHEN** scenario includes network, zones polygons, and OMX
- **THEN** orchestrator produces `net.xml`, `tazs.xml`, `tazRelation.xml`, `trips.xml`, and `routes.xml` in workspace

### Requirement: Strict TAZ and OMX zone alignment

The orchestrator SHALL require OMX zone ids to match polygon `id` or `zone_id` before od2trips. ADR-014 Option A.

#### Scenario: Matching ids

- **WHEN** zones layer ids match OMX zone labels
- **THEN** edgesInDistricts and od2trips complete without zone validation errors

### Requirement: Save binary configurations

The orchestrator SHALL save `.netccfg` and `.polycfg` (and equivalent) for reproducibility following osmBuild pattern. ADR-006.

#### Scenario: Config artifacts retained

- **WHEN** netconvert completes
- **THEN** workspace contains saved configuration alongside `net.xml`

### Requirement: Persist build logs

The orchestrator SHALL retain subprocess stdout/stderr and step metadata in the scenario workspace. PRD §4 traceability.

#### Scenario: Failed netconvert

- **WHEN** netconvert exits non-zero
- **THEN** scenario status is `failed` and logs are listed in artifacts
