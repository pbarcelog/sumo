# ADR-013: SQLite Role

**Status:** Draft — **workshop required**
**Tier:** B

## Context

SQLite is an MVP spatial input (PRD §2). Role may be SpatiaLite geometry, plain attribute tables, or both.

## Options

| Option | Use case |
|---|---|
| **A** | SpatiaLite geometry tables → same as GPKG via pyogrio |
| **B** | Plain SQLite attribute tables joined to spatial layer by key |
| **C** | OMX metadata sidecar in SQLite (unusual — OMX is standalone) |
| **D** | A + B — geometry in SpatiaLite, attributes in relational tables |

## Decision

**Pending workshop with Pablo.**

Recommendation: **Option D** — treat SQLite as flexible container; API introspects schema.

## Consequences

- Normalization layer (ADR-011) needs SQLite schema discovery.
- Document required table/column conventions in API docs.

## References

- PRD §2 open items
