# Data Inventory & Mapping Contract — import-od-demand-geojson

Sources (real files, Karlsruhe federated GeoJSON export):
- OMX: `C:\Users\Pablo Barceló\Downloads\Karlsruhe\Visum_3_modes.omx`
- Zones: `...\zone_centroid.geojson`, `...\zone_polygon.geojson` (polygons diagnostic only v1)
- Connectors: `...\connector.geojson`
- Network: GeoJSON-built `net.xml` (e.g. `c:\tmp\karlsruhe-geojson-net\net.net.xml`)

Demand sibling of `import-od-demand` (SQLite) and network sibling of `import-network-geojson`.
Mirrors AequilibraE field-inventory discipline: **use exported connectors when present**; heuristic
connector generation from zone geometry is **stage 2** (out of scope).

> **Status: SIGNED (apply 2026-06-26).** Karlsruhe measured parity confirms §11 decisions.

---

## 1. SUMO demand is three layers

| Layer | Artifact | GeoJSON federated source | Status |
|---|---|---|---|
| Network | `net.xml` | `node.geojson` + `link.geojson` | **done** (`network-import`) |
| TAZ / districts | `tazs.xml` | `zone_centroid.geojson` + `connector.geojson` | **this change** |
| OD matrix | `tazRelation.xml` | `Visum_3_modes.omx` | **reuse** (`od-import-demand` OMX adapter) |

---

## 2. Crosswalk (measured against real Karlsruhe files)

| Check | Result |
|---|---|
| OMX cores / shape | `Car`, `HVG`, `PUT` — each **726 × 726**; mapping **`NO`** |
| OMX zone labels | **726**, range `110 … 2,000,142` |
| `zone_centroid.geojson` features | **726** (`NO` per feature) |
| **OMX `NO` set == centroid `NO` set** | **TRUE** — 726/726 |
| `zone_polygon.geojson` features | **468** (258 zones centroid-only — no polygon in export) |
| `connector.geojson` features | **2,823** line features |
| Expanded connector rows (AB + `R_*`) | **5,640** GeoJSON (`DIRECTION=O`: 2,820; `DIRECTION=D`: 2,820); **5,646** SQLite |
| **Non-empty expanded rows == SQLite `CONNECTOR`** | **TRUE** — zero diffs on `(ZONENO,NODENO,DIRECTION,TSYSSET)`; 6 SQLite rows with empty `TSYSSET` omitted in GeoJSON export |
| Connector `NODENO` ∈ network nodes | **required** — same rule as SQLite path (validate at apply) |

**Conclusion:** GeoJSON connector export is a **lossless encoding** of SQLite `CONNECTOR` for Karlsruhe.
Option E (ADR-014) applies without spatial guessing.

---

## 3. `zone_centroid.geojson` — field inventory

Geometry: `Point`, WGS84 (EPSG:4326). **Zone identity for v1.**

| Field | Example | SUMO role |
|---|---|---|
| `NO` | `110` | **TAZ id** (== OMX mapping label; preserve verbatim) |
| `NAME` | `Innenstadt_Zirkel` | diagnostic label |
| `TYPENO` | `0` | zone type metadata |
| `S_RESI`, `S_WP`, `F_CULTURE`, `F_SPORT` | counts | socioeconomic metadata — ignored v1 |
| `geometry` | `[lon, lat]` | diagnostic / future polygon fallback — **not** used for connector path |

`zone_polygon.geojson`: `MultiPolygon`, same `NO` on **468** features. **Not required** when
`connector.geojson` is present. The 258 centroid-only zones are mostly external (`NO ≥ 1,000,000`) —
same pattern as SQLite `od-import-demand` §2.4.

---

## 4. `connector.geojson` — field inventory

Geometry: `LineString` (zone↔node access polyline). Each feature carries **AB** and **`R_`** (BA)
attributes — same pattern as `link.geojson`.

| Field (AB / `R_`) | Example | SUMO role |
|---|---|---|
| `ZONENO` / `R_ZONENO` | `110` | zone id |
| `NODENO` / `R_NODENO` | `105225992` | network node (**SUMO node id** == `NODE.NO`) |
| `DIRECTION` / `R_DIRECTION` | `O` / `D` | **`O` → `tazSource`**, **`D` → `tazSink`** |
| `TSYSSET` / `R_TSYSSET` | `BIKE,CAR,HGV,WALK` | mode filter (→ `modes.py`) |
| `TYPENO` / `R_TYPENO` | `9` | connector type metadata |
| `LENGTH` / `R_LENGTH` | `0.237km` | informational |
| `VOL*` | volumes | assignment metadata — ignored |

### 4.1 Expansion rule (GeoJSON → `CONNECTOR` rows)

For each feature:

1. If `TSYSSET` non-empty → emit `(ZONENO, NODENO, DIRECTION, TSYSSET)`.
2. If `R_TSYSSET` non-empty → emit `(R_ZONENO, R_NODENO, R_DIRECTION, R_TSYSSET)`.
3. Empty transport set → skip direction (logged).

Karlsruhe: every feature has `DIRECTION=O` on AB and `R_DIRECTION=D` on BA (2,823 + 2,823 = 5,646).

---

## 5. Connector → `tazs.xml` rule (ADR-014 — same as SQLite path)

Normative rules are **identical** to `import-od-demand/data-inventory.md` §5.3–5.4:

1. Select connectors whose `TSYSSET` contains the target mode token (`CAR` for Car core, etc.).
2. Zone-level O/D synthesis when OMX demand requires a missing direction.
3. Map `NODENO` → incident edges in `net.xml` (`O` out-edges, `D` in-edges); filter by vClass.
4. Uniform `weight="1"` per edge (v1 — `demand-taz-weighting-v1.md`).
5. Fail loud on external demand without resolvable access; exclude zero-demand PuT-only zones.

**Implementation reuse:** `visum_zones.build_taz_records_for_core` — only `read_zone_connectors` gains
a GeoJSON adapter.

---

## 6. OMX → `tazRelation.xml` (unchanged)

Same as archived `od-import-demand` §4: named mapping `NO`, one interval per core, Car→passenger,
HVG→truck, PUT skipped v1 (`skip_put` default true).

---

## 7. Mode mapping (resolved — align with network import)

| VISUM token | SUMO vClass |
|---|---|
| `CAR` | `passenger` |
| `HGV` | `truck` |
| `TRAIN` | `rail_urban` |
| *(others)* | per `modes.py` / `od-import-demand` |

---

## 8. Out of scope (stage 2 — AequilibraE heuristic path)

- Infer connectors from `zone_polygon` + network geometry (k-nearest, nodes-in-polygon).
- `edgesInDistricts.py` polygon fallback when connectors absent.
- PUT trip generation on PuT stop-node connectors.

---

## 9. Fixture plan (synthetic)

- Tiny `zone_centroid.geojson` (2–3 zones) + `connector.geojson` with AB/`R_` rows.
- Cases: O+D CAR connectors, one-way connector feature, PuT-only zone, demand zone with dead node,
  empty `TSYSSET` direction skipped.
- Tiny OMX fixture (reuse `demand/fixtures.py`).
- Tiny `net.xml` with matching node ids.

Real-file smoke: Karlsruhe OMX + GeoJSON zones/connectors + GeoJSON `net.xml` → compare `tazs.xml`
to SQLite path for Car/HVG.

---

## 10. Expected Karlsruhe build counts

| Metric | Expected |
|---|---|
| Zones (centroid) | 726 |
| Connector rows (expanded, non-empty) | 5,640 (5,646 SQLite − 6 empty `TSYSSET`) |
| OMX ↔ zone alignment | 726/726 exact |
| Cores emitted (v1) | Car, HVG (PUT skipped) |
| Excluded PuT-only zero-demand zones | 28 (`2000115…2000142`) |

---

## 11. Modeller sign-off

| Decision | Resolution (signed 2026-06-26) |
|---|---|
| Connector source v1 | **Exported `connector.geojson` only** |
| Zone list authority | **`zone_centroid.geojson` `NO`** |
| Polygon layer | **Diagnostic only** in v1 |
| OMX / PUT / weights / intrazonal | **Same as `od-import-demand`** |
| Heuristic connectors | **Deferred** (stage 2) |

---

## 12. Real-file smoke results

**Date:** 2026-06-26 · **Branch:** `feature/importPoC` · **Network:** `c:\tmp\karlsruhe-geojson-net\net.net.xml`

| Check | Result |
|---|---|
| `test_real_karlsruhe_geojson_connectors_match_sqlite` | **PASS** — 5,640 expanded rows; non-empty set matches SQLite |
| `test_real_karlsruhe_geojson_demand_smoke` | **PASS** (~24 min) |
| Car `tazs.xml` vs SQLite path | **byte-identical** |
| HVG `tazs.xml` vs SQLite path | **byte-identical** |
| Passenger trips (`reachable`) | **> 700,000** |
| Truck trips (`reachable`) | **> 40,000** |
| PuT-only excluded zones | 28 (`2000115…2000142`) |
| SQLite `CONNECTOR` row count | 5,646 |
