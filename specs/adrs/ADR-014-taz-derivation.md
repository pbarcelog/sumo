# ADR-014: TAZ Derivation

**Status:** Accepted
**Tier:** B
**Date:** 2026-06-16

## Context

OD demand requires TAZ definitions (`tazs.xml`) aligned with OMX zone indices/names (ADR-005).

## Options considered

| Option | Approach |
|---|---|
| **A** | GIS polygons → `tools/edgesInDistricts.py` → tazs.xml; OMX zones must match polygon ids |
| **B** | API spatial join: OMX zone centroids → network edges → auto-generate tazs |
| **C** | Client supplies both OMX and matching tazs.xml |
| **D** | B + validation against OMX matrix dimension |

## Decision

**Primary (v1): Option A** — strict identifier alignment, upstream district tooling.

1. Extract zone **polygons** from normalized GIS (GPKG, GeoJSON, SpatiaLite — ADR-011/013).
2. Run **`tools/edgesInDistricts.py`** (or equivalent orchestration) against built `.net.xml` to produce `tazs.xml`.
3. **OMX zone ids must exactly match** polygon `id` / `zone_id` attributes used in tazRelation output (ADR-012).
4. Fail loud if OMX references unknown zones or polygon set is missing expected ids (PRD §4).

### Supported v1 scenarios

| Scenario | Description |
|---|---|
| **Full SQLite model** | Consistent zone ids across geometry, attributes, and OMX in one database |
| **Separate sources** | OD matrix + polygon layers from different uploads; **shared zone codification** required |

### Deferred (v2)

**Fuzzy spatial matching** — centroids, OD, and polygons with **no common codification**, inferring zone membership by centroid-within-polygon geometry only (former Option B/D territory). Not in MVP.

### Polygon layer convention

- Default layer name: **`zones`** (GPKG / GeoJSON / SQLite).
- Override via `?layer=` (ADR-010) or `build_options.layers.zones`.

### Optional fallback

Client MAY upload a pre-built `tazs.xml` when ids already match OMX; API validates dimensions and id sets before od2trips.

## Consequences

- Depends on ADR-011 polygon extraction and ADR-012 strict OMX zone ids.
- See [District tools](../../docs/web/docs/Tools/District.md).

## References

- ADR-005, ADR-011, ADR-012, ADR-013
- `specs/glossary.md` — OMX zones vs TAZ
