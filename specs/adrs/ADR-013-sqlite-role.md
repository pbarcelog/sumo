# ADR-013: SQLite Role

**Status:** Accepted
**Tier:** B
**Date:** 2026-06-16

## Context

SQLite is an MVP spatial input (PRD §2). Role may be SpatiaLite geometry, plain attribute tables, or both.

## Options considered

| Option | Use case |
|---|---|
| **A** | SpatiaLite geometry tables → same as GPKG via pyogrio |
| **B** | Plain SQLite attribute tables joined to spatial layer by key |
| **C** | OMX metadata sidecar in SQLite (unusual — OMX is standalone) |
| **D** | A + B — geometry in SpatiaLite, attributes in relational tables |

## Decision

**Option D** — SQLite is a flexible container for v1:

| Role | Support |
|---|---|
| **SpatiaLite geometry** | Yes — read via pyogrio like GPKG layers |
| **Plain attribute tables** | Yes — join to spatial features by agreed key column |
| **Schema discovery** | API introspects tables; document required conventions in OpenAPI |

### Schema conventions (v1)

- Geometry tables: standard SpatiaLite `geometry_columns` / `spatial_ref_sys` when present.
- Zone identifiers: column `zone_id` (or `id`) on polygon/centroid layers **must match** OMX zone ids when demand is supplied (ADR-014).
- Attribute joins: `build_options.sqlite_joins` maps `{spatial_table, attr_table, key}`.
- Reject ambiguous multi-geometry tables without explicit layer/table selection.

## Consequences

- Normalization layer (ADR-011) implements SQLite introspection alongside GPKG.
- Full-model SQLite scenarios (consistent centroid ↔ OD ↔ zone ids) are first-class v1 path.

## References

- PRD §2
- ADR-011, ADR-014
