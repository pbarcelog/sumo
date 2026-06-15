# ADR-014: TAZ Derivation

**Status:** Draft — **workshop required**
**Tier:** B
**Blocks:** OMX + spatial join

## Context

OD demand requires TAZ definitions (`tazs.xml`) aligned with OMX zone indices/names (ADR-005).

## Options

| Option | Approach |
|---|---|
| **A** | GIS polygons → `tools/edgesInDistricts.py` → tazs.xml; OMX zones must match polygon ids |
| **B** | API spatial join: OMX zone centroids → network edges → auto-generate tazs |
| **C** | Client supplies both OMX and matching tazs.xml |
| **D** | B + validation against OMX matrix dimension |

## Open questions

- Must OMX zone indices match TAZ `id` attributes exactly?
- Partial coverage if GIS zones ⊃ OMX zones?

## Decision

**Pending workshop.**

Recommendation: **Option D** — auto-derive with strict validation; fail if OMX references unknown zones.

## Consequences

- Depends on ADR-011 polygon extraction from GPKG/GeoJSON/SQLite.
- See [District tools](../../docs/web/docs/Tools/District.md).

## References

- ADR-005, ADR-012
- `specs/glossary.md` — OMX zones vs TAZ
