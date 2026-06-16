# ADR-005: OD and Demand Pipeline

**Status:** Accepted (documented from code)
**Tier:** A
**Sources:** `src/od/ODMatrix.cpp`, `docs/web/docs/Demand/Importing_O/D_Matrices.md`

## Context

MVP includes OMX OD matrices. SUMO demand generation uses TAZ definitions and matrix files consumed by `od2trips` / `marouter`.

## Decision

**As-built SUMO formats:**

| Format | Reader | Tool |
|---|---|---|
| tazRelation XML | `ODMatrix::loadMatrix` | od2trips, routeSampler |
| VISUM V-format (and variants) | `ODMatrix.cpp` (`readV`, `readO`) | od2trips |
| PTV `$VMR` etc. | Documented in O/D Matrices doc | od2trips |

**TAZ prerequisites:**

- `tazs` XML defining zones with source/sink edges.
- Created via netedit, or `tools/edgesInDistricts.py` from polygons.

**OMX:**

- **Not supported** natively in SUMO codebase (zero references).
- Requires adapter producing `tazRelation` XML or VISUM V-format (ADR-012).

**Pipeline:**

```
tazs.xml + tazRelation.xml → od2trips → trips.xml → duarouter → routes.xml → sumo
```

## Consequences

- API must implement OMX → tazRelation (or V-format) before demand step.
- OMX zone indices must align with TAZ ids (ADR-014).

## References

- PRD §2 (OMX MVP)
- `specs/interfaces.md` — OMX gap row
