# ADR-009: Code Placement

**Status:** Accepted
**Tier:** B
**Date:** 2026-06-15

## Context

New GIS API code must live in the SUMO tree without modifying upstream files. `tools/import/` already hosts format-specific importers (GTFS, VISUM, MATSim). A universal GIS importer is the same class of component.

## Decision

**Primary package:** `tools/import/gis/`

| Subpath (planned) | Responsibility |
|---|---|
| `tools/import/gis/` | Package root, `README.md` marking fork ownership |
| `tools/import/gis/normalize/` | GIS normalization (ADR-011) |
| `tools/import/gis/omx/` | OMX → tazRelation adapter (ADR-012) |
| `tools/import/gis/orchestrate/` | Scenario build pipeline (ADR-006) |
| `tools/import/gis/api/` | HTTP service (ADR-008, ADR-010) |

**Tests:** `tests/tools/import/gis/**`

### Writable allowlist

Only `tools/import/gis/**` (and its tests) are new code under `tools/`. Siblings such as `tools/import/gtfs/` remain read-only. See `specs/standards/architecture.md`.

### Rejected options

| Option | Reason |
|---|---|
| `tools/contributed/gis-api/` | Unnecessary; new sibling under `import/` is sufficiently isolated |
| Top-level `gis_api/` | Non-idiomatic inside SUMO; worse `SUMO_HOME` / import ergonomics |
| Separate repository | Deferred; single-repo orchestration is simpler for v1 |
| Edit existing `tools/import/*` or `osmBuild.py` | Violates AGENTS.md hard rules |

## Consequences

- Python imports use package path under `tools/import/gis/`.
- `SUMO_HOME` unchanged; `sumolib` imported from existing read-only tree.
- CI adds tests under `tests/tools/import/gis/`.
- New writable root documented in AGENTS.md and `ai/context/key-files.md`.

## References

- PRD §1
- `specs/standards/architecture.md`
- ADR-006 (orchestration)
