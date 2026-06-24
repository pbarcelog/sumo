# omx-adapter

OMX to SUMO demand format adapter (ADR-012).

**PRD:** §2

> **Supersession (2026-06-22):** Normative OMX adapter behavior for named mapping (`NO`), per-core
> intervals (`interval id` = vType), and strict zone alignment is defined in the archived capability
> **`od-import-demand`** (`openspec/specs/od-import-demand/spec.md` and archived
> `openspec/changes/archive/2026-06-22-import-od-demand/data-inventory.md`). This skeleton spec remains as the
> `gis-api-mvp` placeholder; do not archive contradictory interval-slice or default-vType-only
> behavior when merging `import-od-demand`.

## ADDED Requirements

### Requirement: Convert OMX to tazRelation XML

The adapter SHALL read OMX via Python `openmatrix` and emit tazRelation XML validating against ADR-007 XSD. ADR-012. SUMO has no native OMX reader.

#### Scenario: Single matrix OMX

- **WHEN** OMX file contains one non-empty matrix
- **THEN** adapter writes tazRelation XML with relations for all OD pairs

### Requirement: Map OMX time slices to intervals

The adapter SHALL map each OMX matrix or named slice to a `tazRelation` `interval` attribute. ADR-012.

#### Scenario: Multi-slice OMX

- **WHEN** OMX file contains multiple named matrices
- **THEN** each slice produces relations with distinct `interval` values

### Requirement: Vehicle type from OMX metadata

The adapter SHALL map vehicle type from OMX core or file metadata to SUMO `vType` when present; otherwise use default from `build_options.vType`. ADR-012.

#### Scenario: Default vType

- **WHEN** OMX lacks vehicle type metadata
- **THEN** relations use `build_options.vType` or documented default passenger type

### Requirement: Reject dimension mismatch with TAZ

The adapter SHALL fail when OMX zone indices reference ids absent from TAZ polygon set. ADR-014 strict matching.

#### Scenario: Unknown zone id

- **WHEN** OMX references zone id not present in normalized `zones` layer
- **THEN** build fails with explicit zone id in error details
