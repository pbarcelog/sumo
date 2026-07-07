# Data Inventory & Mapping Contract — import-network-geojson

Source: real VISUM GeoJSON export, Karlsruhe.
Files: `C:\Users\Pablo Barceló\Downloads\Karlsruhe\node.geojson`, `...\link.geojson`.

This is the **review gate** for the change: field semantics and translation rules must be
agreed here before the spec scenarios and implementation. It mirrors AequilibraE's
`field_inventory.md` / `mapping_contract.md` — same VISUM source, different target (SUMO microsim).

> **Status: SIGNED OFF (2026-06-25).** Modeller decisions recorded in §11; aligned with
> `import-network-sqlite` Karlsruhe sign-off where the source semantics match.

---

## 1. Observed scale (from the real files)

| Metric | Value |
|---|---|
| Link features | 11,745 |
| Node features | 8,432 |
| Links with `CAR` in `TSYSSET` | 7,678 (all have speed > 0) |
| Links with `V0PRT = 0km/h` | 525 (all non-`CAR`, `LC=PuT`) |
| Links with empty `TSYSSET` (AB) | 2,020 (one-way candidates) |
| Links with empty `R_TSYSSET` (BA) | 2,069 (one-way candidates) |
| Nodes with `NO ≥ 100000` | 329 (PuT / stop-node block) |
| `V0PRT` distribution | 30(4705), 2(1952), 35(1207), 50(865), 45(682), **0(525)**, 5(313), 3(293)… km/h |
| `TSYSSET` top values | `BIKE,CAR,HGV`(3508); `BIKE,BUS,CAR,HGV`(2572); *(empty)*(2020); `BIKE`(1097); `BUS,TRAIN,TRAM`(288)… |

---

## 2. `node.geojson` — field inventory

Geometry: `Point`, WGS84 lon/lat (EPSG:4326).

| Field | Example | SUMO role |
|---|---|---|
| `NO` | `92` | **SUMO node id** (preserve as-is) |
| `geometry` | `[8.4018, 48.9948]` | node x,y (projected by netconvert) |
| `CONTROLTYPE` | `"0"` | signal-control marker → **deferred** to `import-control-plan`; v1 ignores, uses `--tls.guess` |
| `TYPENO` | `2` | node type (metadata; not required for build) |
| `XCOORD`/`YCOORD` | `934238.2 / 6266951.5` | source projected coords — **ignored** (geometry is authoritative) |
| `CODE`,`NAME`,`SCTYPE`,`INSERTPUTNODE` | `""` | preserved-only metadata |
| `T0PRT`,`VOLPRT` | `0min`,`3917.0` | assignment metadata — ignored for network |

---

## 3. `link.geojson` — field inventory

Geometry: `LineString`, WGS84 lon/lat with z=0 (z dropped). Each row carries an **AB** set and an
**`R_`** (BA) set; one row → up to two SUMO edges.

| Field (AB / `R_`) | Example | SUMO role |
|---|---|---|
| `NO` / `R_NO` | `3118` | **edge id**: AB = `NO`, reverse = `-NO` (SUMO convention) |
| `FROMNODENO` / `R_FROMNODENO` | `100201` | edge `from` (reverse swaps) |
| `TONODENO` / `R_TONODENO` | `100202` | edge `to` (reverse swaps) |
| `TSYSSET` / `R_TSYSSET` | `"BUS,TRAIN,TRAM"` | **permission set → `allow`** (empty ⇒ direction omitted) |
| `NUMLANES` / `R_NUMLANES` | `1` | `numLanes` |
| `V0PRT` / `R_V0PRT` | `"30km/h"`, `"0km/h"` | **speed** (private free-flow; see §5) |
| `LENGTH` / `R_LENGTH` | `"0.548km"` | informational; SUMO length derived from geometry |
| `TYPENO` / `R_TYPENO` | `8` | edge-type candidate (fallback) |
| `LC` / `R_LC` | `"PuT"`,`"Collector"` | **edge type** (primary) |
| `CAPPRT`,`CAP_1H`,`CAP_24H` | `0`,`10` | capacity metadata — not used by netconvert v1 |
| `VOL*`,`INSERTPUTLINK` | volumes | assignment metadata — ignored |

---

## 4. Mode → `vClass` mapping  **(resolved — §11)**

`TSYSSET` is a comma list of VISUM transport systems. Each token maps to a SUMO `vClass`:

| VISUM TSys | SUMO `vClass` | Note |
|---|---|---|
| `CAR` | `passenger` | private car |
| `HGV` | `truck` | heavy goods vehicle |
| `BIKE` | `bicycle` | |
| `BUS` | `bus` | |
| `TRAM` | `tram` | (`lightrail` is deprecated → `tram`) |
| `TRAIN` | `rail_urban` | **resolved:** same as SQLite import — urban microsim target |
| `PUTW` | `pedestrian` | "PuT walk" access/egress links |
| `WALK` | `pedestrian` | alias for walk links |

`allow` for an edge = the set of `vClass` mapped from its directional `TSYSSET`. Setting `allow`
explicitly means every unlisted class is disallowed — so PuT-only links automatically exclude
`passenger`/`truck` with **no epsilon-speed hack**.

**Resolved:** one SUMO edge per VISUM link row (separate edges for segregated tram/rail); no
lane-level `allow` splitting in v1.

---

## 5. Speed rule  **(resolved — §11)**

- Convert `V0PRT` `"<n>km/h"` → `n / 3.6` m/s.
- If `V0PRT > 0` → use it.
- If `V0PRT = 0` (PuT-only link) → **fallback by `LC`** (since the PuT speed is not in the GeoJSON
  export; `import-network-sqlite` may supply the real value later). Defaults:

| `LC` | Fallback speed |
|---|---|
| `Major` | 70 km/h |
| `In-urban` | 50 km/h |
| `Collector` | 50 km/h |
| `Ramp` | 50 km/h |
| `PuT` | 50 km/h |
| *(unmapped)* | 50 km/h |

- Every speed substitution is written to the build log (source link `NO`, `LC`, applied speed) for
  PRD §4 traceability.
- Very low real speeds (`2km/h`×1952, `3`,`5km/h`) are kept as-is — **no floor** (§11).

---

## 6. Direction rule

- AB edge created when `TSYSSET` non-empty; reverse edge (`-NO`) created when `R_TSYSSET` non-empty.
- Both empty → link skipped (logged). Both non-empty → bidirectional (two edges).
- Reverse edge uses `R_*` attributes (`R_NUMLANES`, `R_V0PRT`, `R_LC`, swapped from/to).

---

## 7. CRS rule

- Input geometry: EPSG:4326 (WGS84 degrees).
- `netconvert --proj.utm` auto-selects the UTM zone (EPSG:32632 — WGS84 UTM 32N for the Karlsruhe
  reference export) → meters.
- Resolved EPSG and projection parameters are logged; no silent reprojection (config CRS rule).

---

## 8. Control plan (deferred)

`CONTROLTYPE` per node is the hook for real signal timings. v1 leaves control to
`netconvert --tls.guess` (synthetic signals). Real import = future `import-control-plan` change.

---

## 9. Fixture plan (synthetic, compact)

Fixtures encode each rule above so unit tests don't need the 12 MB real files:

- bidirectional car link (`BIKE,CAR,HGV`, real speed) → two edges, `allow` includes passenger.
- one-way link (empty `R_TSYSSET`) → single AB edge.
- **PuT-only link** (`BUS,TRAIN,TRAM`, `V0PRT=0`) → edge with `allow="bus rail_urban tram"`, fallback speed, **no passenger**.
- mixed `LC` values → edge-type assignment.
- multi-vertex geometry + duplicate coordinate → geometry preserved / diagnostic.
- non-WGS84 / missing CRS input → explicit error (fail loud).

Real-file smoke (separate, opt-in): import the actual `node.geojson` + `link.geojson`, assert
counts in range, **zero 0-speed edges**, PuT-only edges disallow `passenger`, and `netconvert`/`sumo`
load the produced `net.xml` without error.

---

## 10. Expected Karlsruhe build counts (real-file smoke)

| Metric | Expected value |
|---|---|
| Node features | 8,432 |
| Link features | 11,745 |
| SUMO edges emitted | 19,401 (AB: 9,725 + BA: 9,676) |
| Skipped directions (empty `TSYSSET`) | 4,089 (AB: 2,020 + BA: 2,069) |
| Links with both directions empty | 843 |
| Speed substitutions (`V0PRT=0`) | 525 link rows × up to 2 directions |
| Resolved projection | EPSG:32632 (WGS84 UTM zone 32N via `--proj.utm`) |

Sample PuT-only link for permission checks: `NO=3118` → edges `3118`/`-3118` with
`allow="bus rail_urban tram"`, no `passenger`.

---

## 11. Modeller sign-off (2026-06-25)

| Decision | Resolution |
|---|---|
| `TRAIN → rail` vs `rail_urban` | **`rail_urban`** — consistent with `import-network-sqlite`; urban microsim target |
| Separate-edge vs shared-lane | **Separate edge per VISUM row** — no lane-level splitting in v1 |
| `LC` fallback table (§5) | **Accepted** as listed; logged on every substitution |
| Low-speed floor (`2km/h` etc.) | **No floor** — keep parsed `V0PRT` when > 0 |
| CRS | **WGS84 in**; fail loud if CRS cannot be established; `--proj.utm` for build |

---

## 12. Real-file smoke results (2026-06-25)

| Check | Result |
|---|---|
| Nodes | 8,432 |
| Edges emitted | 19,401 |
| Skipped directions | 4,089 |
| Speed substitutions logged | 724 |
| `net.xml` edges | 19,401 |
| Zero-speed edges | **0** |
| Resolved EPSG | **EPSG:32632** |
| `NO=3118` PuT-only | `allow` excludes `passenger`; speed 13.89 m/s (50 km/h fallback) |
| `sumolib.net.readNet` | loads without error |
