# Scenario Orchestration

Capability spec for Python orchestration of SUMO binaries in the GIS API fork.

**Change:** document-orchestration-slice
**ADR:** ADR-006
**PRD:** §1, §5

---

## Requirements

### Requirement: Binary resolution via sumolib

The orchestrator MUST resolve SUMO binaries using `sumolib.checkBinary(name, bindir)` and honor `SUMO_HOME`.

#### Scenario: Missing SUMO_HOME

- **WHEN** `SUMO_HOME` is unset and binaries are not on PATH
- **THEN** the orchestrator fails with an explicit error before invoking subprocess

---

### Requirement: Configuration reproducibility

Each netconvert and polyconvert invocation MUST support saving configuration to `.netccfg` / `.polycfg` for audit and replay, following the `osmBuild.py` pattern.

#### Scenario: Replay from saved config

- **WHEN** a `.netccfg` exists from a prior build
- **THEN** `netconvert -c <cfg>` reproduces the same import options

---

### Requirement: Working directory discipline

Subprocess calls MUST use `cwd=output_directory` with relative paths where possible (`getRelative` pattern).

#### Scenario: Artifact isolation

- **WHEN** building scenario `abc123`
- **THEN** all outputs land under the scenario output directory without path leakage

---

### Requirement: Early validation

The orchestrator MUST validate inputs (files exist, output directory exists, required typemaps present) before long-running netconvert execution.

#### Scenario: Missing typemap

- **WHEN** polyconvert typemap is configured but file is missing
- **THEN** fail before netconvert completes (osmBuild early check pattern)

---

### Requirement: Target pipeline steps (API MVP)

The GIS API orchestrator MUST support the following ordered steps (implementation deferred to ADR-008+):

1. GIS normalization (ADR-011)
2. netconvert → `.net.xml`
3. polyconvert → `.poly.xml` (when shapes/TAZ polygons provided)
4. OMX adapter → `tazRelation.xml` (ADR-012)
5. TAZ derivation → `tazs.xml` (ADR-014)
6. od2trips → `.trips.xml`
7. duarouter → `.rou.xml`
8. sumo run (optional, ADR-015)

#### Scenario: Network-only build

- **WHEN** client uploads spatial data without OMX
- **THEN** steps 4–7 are skipped; artifacts include network (and shapes if provided)

#### Scenario: Full scenario with OMX

- **WHEN** client uploads spatial data and OMX matrix
- **THEN** all applicable steps execute; failures at any step abort with logged step name

---

### Requirement: osmBuild as reference implementation

Documentation and new orchestration code MUST treat `tools/osmBuild.py` as the canonical reference for netconvert + polyconvert chaining (PRD §5).

#### Scenario: Developer onboarding

- **WHEN** an agent implements API orchestration
- **THEN** ADR-006 and this spec are consulted before writing subprocess code
