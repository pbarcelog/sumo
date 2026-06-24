# ADR-014: TAZ Derivation

**Status:** Accepted (amended 2026-06-22)
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
| **E** | VISUM SQLite `CONNECTOR` rows → incident **real** net edges as `tazSource`/`tazSink` |

## Decision

**Primary when `CONNECTOR` is present (SQLite path): Option E** — exact zone→node→edge lookup;
proven on Karlsruhe (`import-od-demand`, `data-inventory.md` §2, §9).

1. Read VISUM `ZONE` (`NO`) and `CONNECTOR` (`ZONENO`, `NODENO`, `DIRECTION`, `TSYSSET`) from SQLite.
2. Map each qualifying connector to incident edges in the built `net.xml`:
   - `DIRECTION='O'` → `tazSource` (out-edges from `NODENO`)
   - `DIRECTION='D'` → `tazSink` (in-edges to `NODENO`)
3. Filter edges by target vClass (`passenger` / `truck` per mode); union and deduplicate per zone
   and direction.
4. **v1 edge weights:** assign uniform `weight="1"` to every `tazSource`/`tazSink`; do **not** read
   VISUM `WEIGHT(PRT)` / `WEIGHT(PUT)` — see
   [`specs/assumptions/demand-taz-weighting-v1.md`](../assumptions/demand-taz-weighting-v1.md).
5. Emit **one `tazs.xml` per mode** (same zone ids, mode-filtered edges).
6. Apply connector-direction synthesis and external-only fail-loud rules from
   `openspec/changes/import-od-demand/data-inventory.md` §5.3–5.4 (zone-level O/D mirroring; drop
   intrazonal OMX when no spawn/absorb path).

**Implementation:** `tools/import/gis/normalize/visum_zones.py`.

**Fallback when `CONNECTOR` is absent (GeoJSON / polygon-only sources): Option A** — strict identifier
alignment, upstream district tooling.

1. Extract zone **polygons** from normalized GIS (GPKG, GeoJSON, SpatiaLite — ADR-011/013).
2. Run **`tools/edgesInDistricts.py`** (or equivalent orchestration) against built `.net.xml` to produce
   `tazs.xml`.
3. **OMX zone ids must exactly match** polygon `id` / `zone_id` attributes used in tazRelation output
   (ADR-012).
4. Fail loud if OMX references unknown zones or polygon set is missing expected ids (PRD §4).

AequilibraE-style connector inference (`k_nearest_in_zone`, nodes within polygon) is recorded as the
starting point for a future GeoJSON fallback when connectors are absent — not in v1.

### Supported v1 scenarios

| Scenario | TAZ path |
|---|---|
| **VISUM SQLite + OMX** | `CONNECTOR` → incident net edges (primary) |
| **Full SQLite model** | Same as above when connectors present; polygons diagnostic only |
| **GeoJSON / GPKG only** | Polygons + `edgesInDistricts.py` (fallback) |
| **Separate sources** | OD matrix + polygon layers; **shared zone codification** required |

### Deferred (v2)

**Fuzzy spatial matching** — centroids, OD, and polygons with **no common codification**, inferring zone
membership by centroid-within-polygon geometry only (former Option B/D territory). Not in MVP.

### Polygon layer convention

- Default layer name: **`zones`** (GPKG / GeoJSON / SQLite).
- Override via `?layer=` (ADR-010) or `build_options.layers.zones`.

### Optional fallback

Client MAY upload a pre-built `tazs.xml` when ids already match OMX; API validates dimensions and id
sets before od2trips.

## Consequences

- Depends on ADR-011 polygon extraction (fallback path), ADR-012 strict OMX zone ids, and
  `import-network-sqlite` preserving `NODE.NO` / edge ids for connector resolution.
- VISUM-faithful connector weight mapping deferred; v1 uses uniform weights (assumptions doc above).
- See [District tools](../../docs/web/docs/Tools/District.md) for polygon path.

## References

- ADR-005, ADR-011, ADR-012, ADR-013
- `specs/assumptions/demand-taz-weighting-v1.md` — v1 uniform TAZ edge weights
- `openspec/changes/import-od-demand/data-inventory.md` — CONNECTOR → edge rules (Karlsruhe evidence)
- `specs/glossary.md` — OMX zones vs TAZ
