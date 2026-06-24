# Data Inventory & Mapping Contract — import-network-sqlite

Source: real VISUM SQLite export, Karlsruhe.
File: `C:\Users\Pablo Barceló\Downloads\Karlsruhe\Karlsruhe-sqlite.sqlite3` (~31.8 MB).
VISUM version: `2026.01` (FILETYPE `Net`, VERSNR `19.0`, LANGUAGE `ENG`, UNIT `KM`).

This is the **review gate** for the change: every field semantic and translation rule below must be
signed off before spec scenarios are treated as final and before any `/sumo-apply`. It mirrors
AequilibraE's `field_inventory.md` / `mapping_contract.md` (same VISUM source, different target —
SUMO microsimulation vs AequilibraE static assignment). All counts are measured from the real DB.

> **Status: DRAFT — needs modeller sign-off.** Items flagged **(confirm)** are open decisions.

This file is the data-rich sibling of `import-network-geojson/data-inventory.md`. The decisive
difference: the SQLite export carries **per-link-type, per-mode speeds** (`LINKTYPE`) and **PuT travel
times** (`LINK.T_PUTSYS(*)`), so PuT-only links that the GeoJSON export left at `V0PRT=0` now get a
**real positive speed with no fallback table and no epsilon hack**.

---

## 1. Observed scale (measured from the real DB)

| Metric | Value |
|---|---|
| `NODE` rows | 8,432 |
| `LINK` rows (**directed** — each direction is its own row) | 23,490 |
| Distinct `LINK.NO` (undirected link ids; every NO has exactly 2 rows) | 11,745 |
| `LINK` rows with non-empty `TSYSSET` (→ candidate SUMO edges) | 19,401 |
| `LINK` rows with empty `TSYSSET` (closed direction → skip + log) | 4,089 |
| `LINK.NO` with exactly one empty direction (one-way) | 2,403 |
| `LINK.NO` with both directions empty (fully skipped) | 843 |
| `LINK` rows with `V0PRT = 0` (private free-flow absent; non-`CAR`) | 1,056 |
| `LINK` rows containing `CAR` and `V0PRT = 0` | **0** (invariant: every car link has positive `V0PRT`) |
| `LINK` rows whose `TYPENO` is **missing** from `LINKTYPE` | **0** (every link type resolves) |
| Directed links with non-empty `TSYSSET` that resolve to **0/unknown** speed under the §5 rule | **0** |
| `CONNECTOR` rows (zone↔node, `O`/`D`) | 5,646 (2,823 `O` + 2,823 `D`) |
| `ZONE` rows | 726 |
| `TSYS` rows | 8 |
| `MODE` rows | 5 |
| `LINKTYPE` rows | 73 |
| `LANE` rows | 21,239 |
| `LINKPOLY` directed links carrying intermediate geometry vertices | 3,045 (6,384 vertices) |
| `NODE.NO` range | 92 … 305,110,027 |
| Nodes `NO ≥ 100000` (PuT / stop-node block) | 8,330 |
| Nodes `NO < 100000` (PrT block) | 102 |
| `NODE.CONTROLTYPE` distribution | `0`: 7,949 · `2`: 2 · `3`: 481 (signalized) |

`V0PRT` (private free-flow, km/h) top values: `30`(9391), `2`(3941), `35`(2421), `50`(1729),
`45`(1342), **`0`(1056)**, `5`(626), `3`(586), `40`(490), `55`(357)…

`LINK.TSYSSET` top values: `BIKE,CAR,HGV`(7005); `BIKE,BUS,CAR,HGV`(5127); *(empty)*(4089);
`BIKE`(2196); `BIKE,BUS,CAR,HGV,PUTW`(1159); `BUS,CAR,HGV`(983); `BIKE,PUTW`(590);
`BUS,TRAIN,TRAM`(577); `CAR,HGV`(530); `PUTW`(239); `BIKE,BUS,CAR,HGV,TRAM`(162)…

---

## 2. Transport systems (`TSYS`) and modes (`MODE`)

`TSYS` (8 rows) is the authoritative token list; `TYPE` classifies private vs public:

| `CODE` | `NAME` | `TYPE` | SUMO `vClass` (this change) | Note |
|---|---|---|---|---|
| `CAR` | Car | PrT | `passenger` | private car |
| `HGV` | HGV | PrT | `truck` | heavy goods |
| `BIKE` | Bike | PrT | `bicycle` | |
| `BUS` | Bus | PuT | `bus` | |
| `TRAM` | Tramway / Streetcar | PuT | `tram` | (`lightrail` deprecated → `tram`) |
| `TRAIN` | Train | PuT | `rail_urban` | **(confirm)** `rail` vs `rail_urban` (see §4) |
| `PUTW` | PuT Walk | PuTWalk | `pedestrian` | PuT access/egress walk |
| `WALK` | PrT Walk | PrT | `pedestrian` | private walk (rare on `LINK`; common on `CONNECTOR`) |

`MODE` (5 rows) groups TSys into demand modes: `B`=`BIKE`, `C`=`CAR`, `H`=`HGV`, `W`=`WALK`,
`PuT`=`BUS,PUTW,TRAIN,TRAM` (interchangeable). Modes drive demand, not the network build; for v1 the
network import keys off `TSYS`/`TSYSSET` directly.

---

## 3. Network tables — field inventory

### 3.1 `NODE` (8,432) — SUMO nodes

Primary key `NO`. Coordinates are **projected meters** in the VISUM CRS (see §7), not lon/lat.

| Field | Example | SUMO role |
|---|---|---|
| `NO` | `92` | **SUMO node id** (preserve verbatim) |
| `XCOORD` / `YCOORD` | `934238.21 / 6266951.47` | node x/y (reprojected per §7) |
| `ZCOORD` | `0.0` | ignored (z dropped) |
| `CONTROLTYPE` | `"0"`,`"3"` | signal hook → **deferred** to `import-control-plan`; v1 ignores, uses `--tls.guess` |
| `TYPENO` | `2` | node type metadata; not required for build |
| `MAINNODENO` | `0` | main-node grouping; not used in v1 |
| `CODE`,`NAME`,`NOTES`,`ICA*`,`SBA*`,`T0PRT`,`CAPPRT` | — | metadata / assignment fields — ignored |

### 3.2 `LINK` (23,490 directed rows) — SUMO edges

Composite primary key `(NO, FROMNODENO, TONODENO)`. **Each direction is a separate row**; the two
rows of a link share `NO` with swapped `FROMNODENO`/`TONODENO`. This differs from the GeoJSON export
(one row carrying AB + `R_*`). `USERDIRECTION = 0` for all rows (not a usable direction flag).

| Field | Example | SUMO role |
|---|---|---|
| `NO` | `3118` | undirected link id; **edge id** = signed `NO` per §6 |
| `FROMNODENO` / `TONODENO` | `100201 / 100202` | edge `from` / `to` |
| `TSYSSET` | `"BUS,TRAIN,TRAM"` | **permission set → `allow`** (empty ⇒ direction skipped, §6) |
| `TYPENO` | `8` | **→ `LINKTYPE.NO`**: primary edge `type` + speed source (§5) |
| `LC` | `"PuT"`,`"Collector"` | human-readable link class (secondary `type` label / diagnostics) |
| `NUMLANES` | `1` | `numLanes` (§ lanes); `0` on closed directions |
| `V0PRT` | `30.0`, `0.0` | private free-flow speed **km/h** (0 ⇒ no private traffic, not "no speed") |
| `LENGTH` | `0.548` | link length **km**; SUMO length derived from geometry (informational) |
| `T_PUTSYS(BUS)` / `(TRAM)` / `(TRAIN)` / `(PUTW)` | `39` | **PuT travel time (seconds)** per PuT system → derives PuT speed `LENGTH/time` (§5) |
| `CAPPRT`,`CAP_1H`,`CAP_24H` | `0` | capacity metadata — not used by netconvert v1 |
| `ADDVAL_TSYS(*)`,`TOLL_*`,`COSTRATE*`,`ICA*`,`SBA*` | — | assignment / toll / capacity-analysis fields — ignored |

### 3.3 `LINKTYPE` (73) — **per-type, per-mode speed source (the key advantage)**

Join `LINK.TYPENO → LINKTYPE.NO`. Every `LINK.TYPENO` resolves (0 misses measured).

| Field | Example | Role |
|---|---|---|
| `NO` | `33` | link-type id (join key) |
| `NAME` | `"2_urban_2_LANES_SPEED_ 50"` | type label |
| `TSYSSET` | `"BIKE,BUS,CAR,HGV,PUTW"` | type's permitted systems (diagnostic) |
| `V0PRT` | `50.0` | type default private free-flow **km/h** |
| `VMAX_PRTSYS(CAR)` / `(HGV)` / `(BIKE)` / `(WALK)` | `50/50/3/2` | **per-PrT-mode max speed km/h** |
| `VDEF_PUTSYS(BUS)` / `(TRAM)` / `(TRAIN)` / `(PUTW)` | `30/50/50/3` | **per-PuT-mode default speed km/h** |
| `NUMLANES`,`CAPPRT`,`RANK`,`HBEFA_ROADTYPE`,`RLS19_ROADTYPE` | — | metadata; `HBEFA_ROADTYPE` is a future emissions hook |

Only **4** of 73 link types have `V0PRT = 0` (rail/tram/planned: `NO` 6, 8, 9, 98); each still carries
positive `VDEF_PUTSYS(*)` (50 km/h), so PuT-only edges always resolve to a positive speed.

### 3.4 `LINKPOLY` (6,384 vertices) — link geometry

`(FROMNODENO, TONODENO, INDEX, XCOORD, YCOORD, ZCOORD)`. Intermediate shape vertices for 3,045
directed links; remaining links are straight (from-node → to-node only). Reverse direction reuses the
forward vertices in reverse order (AequilibraE pattern). Coordinates reprojected per §7.

### 3.5 `LANE` (21,239) — lane detail (evaluated; see § lanes)

`(FROMNODENO, TONODENO, INDEXATFROMNODE, INDEXATTONODE, WIDTH, TSYSSET, …)`. Per-lane `TSYSSET`
exists. **Measured: 0 directed links have lanes with differing `TSYSSET`** — i.e. no dedicated-PT-lane
on a shared corridor anywhere in this export. Decision in § lanes.

### 3.6 `CONNECTOR` (5,646) — zone↔node access (deferred to demand phase)

`(ZONENO, NODENO, DIRECTION 'O'/'D', TSYSSET, T0_TSYS(CAR/BIKE/HGV/PUTW/WALK), …)`. Connectors link
zone centroids to network nodes for OD loading. **Out of scope for network build**; documented here
because `import-od-demand` / TAZ derivation (ADR-014) will consume them.

### 3.7 `ZONE` (726) — TAZ source (deferred)

`(NO, NAME, XCOORD, YCOORD, SURFACEID, …)`. Centroid + surface polygon source for TAZ. Deferred to
TAZ/demand changes (ADR-014); the network build does not emit zones.

---

## 4. Mode → `vClass` mapping **(confirm)**

`TSYSSET` is a comma list of `TSYS.CODE` tokens. Each token maps to a SUMO `vClass`:

| VISUM TSys | SUMO `vClass` | Note |
|---|---|---|
| `CAR` | `passenger` | private car |
| `HGV` | `truck` | heavy goods vehicle |
| `BIKE` | `bicycle` | |
| `BUS` | `bus` | |
| `TRAM` | `tram` | physically separable; see lanes note |
| `TRAIN` | `rail_urban` | **resolved**: microsim targets urban commuters; VISUM does not split urban vs long-distance rail, and urban models typically omit long-distance services, so `rail_urban` is the safe choice |
| `PUTW` | `pedestrian` | PuT access/egress walk |
| `WALK` | `pedestrian` | private walk |

- The map **MUST be configurable** via `build_options.mode_mapping` (AequilibraE pattern).
- Unmapped `TSYSSET` tokens **MUST be reported** (warning, with source `NO`) and never silently
  dropped. Carried over from `import-network-geojson` for VISUM-family consistency.
- `allow` for an edge = the set of `vClass` from its directional `TSYSSET`. Explicit `allow` means every
  unlisted class is disallowed, so PuT-only edges exclude `passenger`/`truck` automatically.
- **Note:** both `TRAIN` and `WALK`/`PUTW` map can collide on `vClass`; `TRAIN→rail_urban` is the only
  one needing sign-off.

---

## 5. Speed rule — **real per-mode speeds, no fallback table, no epsilon (the SQLite win)**

SUMO requires a single positive `speed` per edge (a ceiling), but VISUM speeds are per-mode. Rule:

1. Resolve the edge's link type `lt = LINKTYPE[LINK.TYPENO]`.
2. Build the candidate speed set from the edge's **allowed** TSys tokens:
   - PrT tokens: `CAR→VMAX_PRTSYS(CAR)`, `HGV→VMAX_PRTSYS(HGV)`, `BIKE→VMAX_PRTSYS(BIKE)`,
     `WALK→VMAX_PRTSYS(WALK)`.
   - PuT tokens: `BUS→VDEF_PUTSYS(BUS)`, `TRAM→VDEF_PUTSYS(TRAM)`, `TRAIN→VDEF_PUTSYS(TRAIN)`,
     `PUTW→VDEF_PUTSYS(PUTW)`.
   - Also include `LINK.V0PRT` when `> 0`.
3. **Edge `speed` (ceiling, m/s) = max(candidate speeds) / 3.6.** Always `> 0` (proven over all 19,401
   transport-bearing directed links; zero unresolved).
4. **Per-mode restrictions (resolved):** A SUMO edge has a single `speed` applied to all vehicles; the
   only way to cap individual classes differently on the same edge is a `<restriction vClass="..."
   speed="..."/>` on the edge `type`. Keep the ceiling = fastest allowed mode and emit a `<restriction>`
   for **every** allowed `vClass` whose `LINKTYPE` per-mode speed is below the ceiling (not just bike and
   pedestrian) — **never** split lanes. Emitting them for all modes costs nothing extra and preserves
   VISUM's full per-mode speed fidelity (e.g. on a `CAR,HGV,BUS` type with CAR 50 / HGV 30 / BUS 45 the
   ceiling is 50 with restrictions `truck`=30 and `bus`=45). The coherence rule in step 7 still flags the
   rare case where even the ceiling is implausibly low on a motorized edge.
5. **PuT-only edges** (`V0PRT = 0`): step 2 yields a positive `VDEF_PUTSYS(*)` (≥ 50 km/h on the 4
   zero-`V0PRT` types). No `LC` fallback table is needed (unlike the GeoJSON change), and no epsilon.
6. **Cross-check (diagnostic, not authoritative):** PuT speed can also be derived as
   `LENGTH / T_PUTSYS(sys)`. Verified on link `NO=3118`: `548 m / 39 s = 14.05 m/s ≈ 50.6 km/h`, matching
   `VDEF_PUTSYS(BUS)=50`. The importer SHOULD log when the two sources disagree beyond a tolerance.
7. **Low speeds: kept, with a coherence log (resolved).** Very low real speeds exist (`2`,`3`,`5` km/h)
   and are **kept as-is** (not floored). However, a low ceiling is only expected on walk/bike-type
   edges. When the resolved ceiling is low (≤ a configurable threshold, default 5 km/h) on an edge whose
   `allow` includes a **motorized** class (anything other than `bicycle`/`pedestrian` — e.g.
   `passenger`, `truck`, `bus`, `tram`, `rail_urban`), the importer writes a **coherence warning**
   (source `NO`, `TYPENO`, allowed modes, ceiling) so the modeller can inspect that specific link. The
   edge is still built (no drop, no floor).
8. Every speed resolution writes a log line (source `NO`, `TYPENO`, allowed modes, chosen ceiling,
   any per-mode restriction) for PRD §4 traceability.

---

## 6. Direction rule

The DB stores both directions explicitly. For each `LINK.NO`:

- Group the (normally 2) rows; sort by `(FROMNODENO, TONODENO)`. The first is the **AB** row; the
  reverse row is the one with swapped `from`/`to`. (AequilibraE's canonical ordering — reused for
  deterministic, reproducible sign assignment.)
- **Edge id:** AB → `NO`; reverse (BA) → `-NO` (SUMO convention).
- Create the AB edge only when AB `TSYSSET` is non-empty; create the BA edge only when BA `TSYSSET`
  is non-empty. A direction with empty `TSYSSET` is **skipped and logged** (4,089 such rows).
- Both directions empty (843 link ids) ⇒ the whole link is skipped and logged.
- Each direction uses its own row's `TSYSSET`, `TYPENO`, `NUMLANES`, `V0PRT`, geometry orientation.
- **Resolved:** the AB/BA sign convention uses the `(FROMNODENO, TONODENO)` sort key (`+NO` to the
  first-sorting row, `-NO` to its swapped partner). `USERDIRECTION` carries no orientation signal here,
  so the sort key gives a deterministic, reproducible assignment. The sign has no physical/behavioural
  meaning — it only makes the two edge ids unique.

---

## 7. CRS rule — **projected source, explicit reprojection (differs from GeoJSON)**

- `NETWORK.PROJECTIONDEFINITION` (WKT) = `Sphere_Mercator` on a sphere datum
  (`GCS_Sphere`, `SPHEROID["Sphere",6371000,0]`, `PROJECTION["Mercator"]`, `UNIT["Meter",1]`) — i.e.
  ESRI `Sphere_Mercator`, **not** WGS84 and **not** UTM. Coordinates are meters
  (x ≈ 883k–1,056k, y ≈ 6.18M–6.35M).
- Unlike `import-network-geojson` (WGS84 → `netconvert --proj.utm`), SUMO cannot auto-UTM directly from
  this sphere-Mercator frame (datum/units mismatch). The importer **reprojects coordinates with pyproj**
  from the source WKT to the target network CRS (default **EPSG:25832**, UTM 32N for Karlsruhe), then
  feeds plain cartesian coordinates to `netconvert` (no further netconvert projection).
- Source CRS is read from `PROJECTIONDEFINITION`; if absent, fail loud (no silent default), with an
  optional `build_options.crs` override (ADR-011 CRS policy).
- Resolved source WKT and target EPSG are logged; no silent reprojection (PRD §4, config CRS rule).
- **Resolved (importer decision):** reproject **in Python with pyproj** from the embedded source WKT to
  **EPSG:25832** (UTM 32N) by default, overridable via `build_options.crs`, and feed plain cartesian
  coordinates to netconvert. Rationale: the source is on a *sphere* datum (`Sphere_Mercator`), so a
  datum-aware transform is required; doing it explicitly in pyproj (rather than handing the WKT to
  netconvert) keeps reprojection testable and logged, matches ADR-011 ("always reproject before
  netconvert"), and corrects the Mercator scale distortion (≈ ×1.5 at this latitude) that would
  otherwise inflate edge lengths and the length-vs-speed relationship.

---

## 8. Lanes — **evaluated, deferred with evidence**

- `LINK.NUMLANES` distribution: `1`(17,944), `0`(3,940 — closed directions), `2`(1,538), `3`(61),
  `4`(7). Mapped directly to SUMO `numLanes` (skip rows with `NUMLANES = 0` / empty `TSYSSET`).
- **Per-lane mode permissions (resolved — deferred with evidence):** the `LANE` table (21,239 rows)
  carries per-lane `TSYSSET`, but **0 directed links have lanes with more than one distinct `TSYSSET`** —
  there is no dedicated-PT-lane-on-shared-corridor anywhere in this export. Therefore per-lane `allow`
  modelling is **not supported by this data and is deferred**; `numLanes` is taken from `LINK.NUMLANES`,
  and physically separate tram/rail remains a separate edge (its own VISUM link row).
- **`LANE.WIDTH` (resolved — deferred, unrelated to modes):** `WIDTH` is the *physical* width of a lane
  in metres and has **no bearing on which modes may use the lane**; it was mistakenly bundled with the
  permission question above. It is a purely cosmetic/geometric attribute, not needed for a runnable net,
  so v1 uses SUMO's default lane width and **does not** ingest `LANE.WIDTH`.

---

## 9. Control plan (deferred)

`NODE.CONTROLTYPE` (`3` = signalized on 481 nodes) plus `SIGNALCONTROL`(3), `SIGNALGROUP`(13),
`SIGNALGROUPTOLANETURN`(33), `LANETURN`(46) hold real signal data, but full timings are sparse. v1
uses `netconvert --tls.guess`; real signal import is deferred to `import-control-plan`. `CONTROLTYPE`
and the signal tables are noted as hooks.

---

## 10. Fixture plan (synthetic, compact)

Fixtures encode each rule so unit tests don't need the 31.8 MB DB. A tiny synthetic SQLite DB with the
required tables (`NETWORK`, `NODE`, `LINK`, `LINKTYPE`, `TSYS`, plus optional `LINKPOLY`):

- bidirectional car link (`BIKE,CAR,HGV`, `V0PRT>0`) → two edges, `allow` includes `passenger`.
- one-way link (BA direction `TSYSSET` empty) → single AB edge; omitted reverse logged.
- **PuT-only link** (`BUS,TRAIN,TRAM`, `V0PRT=0`, link type 8) → edge `allow="bus rail_urban tram"`,
  **positive** speed from `VDEF_PUTSYS`, **no `passenger`**, no epsilon.
- mixed-speed link (e.g. `BIKE,CAR` where bike `VMAX` < car `VMAX`) → ceiling = car speed + a
  `<restriction vClass="bicycle" .../>`.
- link with `LINKPOLY` vertices → geometry shape preserved (and reversed for BA).
- link whose `TSYSSET` has an unmapped token (e.g. `FERRY`) → mapped modes kept, unmapped token
  reported (warning), edge not dropped.
- projected-CRS fixture (sphere-Mercator WKT) reprojected to UTM; and a **missing-`PROJECTIONDEFINITION`**
  fixture → explicit error (fail loud).
- malformed / non-SQLite input and missing-required-table fixture → explicit error.

Real Karlsruhe smoke (separate, opt-in): import the actual DB, assert counts in range (≈ 8,432 nodes;
≈ 19,401 directed candidate edges minus fully-skipped; 843 links fully skipped), **zero zero-speed
edges**, sampled PuT-only edge (e.g. `NO=3118`) disallows `passenger`, and `netconvert`/`sumo` load the
produced `net.xml` without error. Resolved EPSG and counts recorded back here.

---

## 11. Sign-off log (all resolved 2026-06-18)

1. **`TRAIN → rail_urban`** (§4) — **resolved.** Microsim targets urban commuters; VISUM does not
   distinguish urban vs long-distance rail and urban models typically omit long-distance services, so
   `rail_urban` is the safe mapping.
2. **Per-mode `<restriction>` scope** (§5 step 4) — **resolved (updated 2026-06-18).** Single edge
   ceiling = fastest allowed mode; emit a `<restriction>` for **every** allowed `vClass` whose
   `LINKTYPE` speed is below the ceiling (all modes, not just bike/pedestrian — same cost, full fidelity).
   `<restriction>` is a property of the SUMO edge **type**, so the ceiling and restrictions are computed
   per type (merged across edges sharing it), not per individual edge. The §5 step 7 coherence log still
   catches implausibly low ceilings on motorized edges.
3. **Lane modelling** (§8) — **resolved.** Per-lane `allow` deferred (no dedicated-PT-lane data).
   `LANE.WIDTH` deferred and decoupled — it is physical lane width, unrelated to mode permissions.
4. **CRS target** (§7) — **resolved (importer decision).** Reproject in Python with pyproj from the
   embedded WKT to `EPSG:25832` (overridable), then feed cartesian to netconvert; corrects sphere-
   Mercator scale distortion and keeps reprojection explicit and logged.
5. **Direction sign convention** (§6) — **resolved.** `(FROMNODENO, TONODENO)` sort decides `+NO`/`-NO`;
   deterministic, no physical meaning.
6. **Low speeds** (§5 step 7) — **resolved.** Kept as-is (not floored); a coherence warning is logged
   when a low ceiling (≤ 5 km/h, configurable) lands on an edge that allows a motorized class
   (anything other than `bicycle`/`pedestrian`), for modeller inspection.

---

## 12. Apply results (recorded 2026-06-18)

Normalization run of the real `Karlsruhe-sqlite.sqlite3` via
`gis.orchestrate.netbuild.build_network_from_sqlite(..., run_netconvert=False)`:

| Metric | Result | Matches §1 prediction |
|---|---|---|
| Nodes emitted | 8,432 | ✅ |
| Directed edges emitted | 19,401 | ✅ |
| Edge types emitted | 71 | (2 of 73 link types carry no surviving edge) |
| Skipped directions (empty `TSYSSET`) | 4,089 | ✅ |
| **Zero-speed edges** | **0** | ✅ (the decisive invariant) |
| Unmapped TSys tokens | none | ✅ |
| Coherence warnings (low ceiling on motorized edge) | 372 | links for modeller inspection (e.g. link types 90/95 at ≤ 5 km/h) |
| Source CRS | `Sphere_Mercator` WKT | ✅ |
| Target CRS | `EPSG:25832` | ✅ |
| `NO=3118` (PuT-only) edges | `allow="bus rail_urban tram"`, speed 13.89 m/s (50 km/h), no `passenger` | ✅ |

**netconvert build + load** (task 6.4, verified 2026-06-18): `pip install eclipse-sumo` 1.27.0 supplies
`netconvert` on `PATH`. Pytest smoke:

- `test_build_produces_loadable_net` — synthetic fixture → `net.xml` loads via `sumolib.net.readNet`,
  all edge speeds > 0.
- `test_real_karlsruhe_build_loads` — real Karlsruhe DB → `net.xml` builds and loads, all edge speeds
  > 0; source WKT `Sphere_Mercator`, target `EPSG:25832`.

Full suite: 23 passed, 0 skipped (`tests/tools/import/gis/network/test_visum_sqlite.py`).
