# Data Inventory & Mapping Contract — import-od-demand

Sources (real files, Karlsruhe):
- OMX matrix: `C:\Users\Pablo Barceló\Downloads\Karlsruhe\Visum_3_modes.omx` (~1.77 MB).
- VISUM SQLite: `C:\Users\Pablo Barceló\Downloads\Karlsruhe\Karlsruhe-sqlite.sqlite3` (~31.8 MB)
  — same export `import-network-sqlite` built `net.xml` from (VISUM `2026.01`, UNIT `KM`).
- Built network: `net.xml` from `import-network-sqlite` (`NODE.NO` = SUMO node id; `LINK.NO`/`-NO` =
  SUMO edge id — both preserved verbatim).

This is the **review gate**: every field semantic, the OMX↔ZONE↔net crosswalk, and every translation
rule below must be signed off (§11) before spec scenarios are treated as final and before any
`/sumo-apply`. It is the demand sibling of `import-network-sqlite/data-inventory.md` and mirrors
AequilibraE's field-inventory / mapping-contract discipline (same VISUM source; SUMO microsim target
vs AequilibraE static assignment). **All counts below are measured from the real files.**

> **Status: DRAFT — needs modeller sign-off.** Items flagged **(confirm)** are open decisions (§10).

---

## 1. SUMO demand is three layers (not one file)

| Layer | Artifact | Source | Status |
|---|---|---|---|
| Network | `net.xml` | VISUM `NODE`/`LINK` (SQLite) | **done** (`import-network-sqlite`) |
| TAZ / districts | `tazs.xml` | VISUM `ZONE` + `CONNECTOR` (SQLite) | **this change** |
| OD matrix | `tazRelation.xml` | OMX cores (`Visum_3_modes.omx`) | **this change** |

`od2trips` consumes all three: `tazs.xml` + `tazRelation.xml` + `net.xml` → `trips.xml`. The OMX matrix
carries trip counts between zone ids only — **no** connector/access information. VISUM `CONNECTOR` rows
(zone↔node, `O`/`D`) are the macroscopic access model and must become `tazSource`/`tazSink` edge
assignments (ADR-005, ADR-014).

---

## 2. The crosswalk (proven against the real files — the decisive result)

| Check | Result |
|---|---|
| OMX core count / shape | 3 cores (`Car`, `HVG`, `PUT`), each **726 × 726**; `OMX_VERSION 0.2`, root `SHAPE [726 726]` |
| OMX zone mapping | named mapping **`NO`**, 726 labels, range **110 … 2,000,142** |
| `ZONE` rows / id | **726**, primary key `NO`, range **110 … 2,000,142**, 726 distinct |
| **OMX `NO` set == `ZONE.NO` set** | **TRUE** — 726/726, **0** in-OMX-not-in-ZONE, **0** in-ZONE-not-in-OMX |
| `CONNECTOR` rows | **5,646** = **2,823 `O`** + **2,823 `D`** |
| `CONNECTOR` distinct zones / nodes | distinct `ZONENO` **726** (every zone connected); distinct `NODENO` **1,792** |
| Every zone has an `O` and a `D` connector (any TSys) | **yes** — 0 zones missing `O`, 0 missing `D` |
| All `CONNECTOR.NODENO` ∈ `NODE.NO` (8,432 nodes) | **1,792 / 1,792** |
| CAR-connector `NODENO` ∈ `NODE.NO` | **1,387 / 1,387** |
| CAR-connector `NODENO` that are `LINK` endpoints (→ became SUMO edges) | **1,386 / 1,387** (1 node not a link endpoint — see §7 anomaly) |
| PrT (`CAR`) `O`-connectors per zone | min **0**, median **2**, max **8** |

**Conclusion:** the SQLite `CONNECTOR` path gives an exact, lookup-based zone→edge access model. No
spatial polygon guess is needed for Karlsruhe (unlike the GeoJSON `edgesInDistricts` fallback, where
only 468/726 zones have polygons — see `import-network-geojson/data-inventory.md` and the AequilibraE
handoff). This is why the `CONNECTOR` path is **primary** here (ADR-014 extension, §9).

### 2.4 External / PuT-only zones (the key fail-loud edge case)

- **258** zones have `NO ≥ 1,000,000` (VISUM external numbering). Of these, **230** carry CAR
  connectors; **28** do not.
- The **28** zones `2000115 … 2000142` have **only `PUTW` connectors** (70 connector rows total) and
  carry **zero demand** in **all three** cores (Car/HVG/PUT out = 0, in = 0).
- **Contract:** zones with no PrT connector **and** zero PrT demand are **reported and excluded** from
  the PrT `tazs.xml`, not errored. A zone that has demand but no resolvable connector edge is a
  **fail-loud** error (§5).

---

## 3. OMX field inventory (`Visum_3_modes.omx`)

Root attributes: `OMX_VERSION = 0.2`, `SHAPE = [726 726]`. One named mapping: **`NO`** (zone numbers).

| Core | `NAME` | `CODE` | `NO` | `MATRIXTYPE` | dtype | non-zero cells | total trips (Σ) | max cell | intrazonal (diag Σ) |
|---|---|---|---|---|---|---|---|---|---|
| `Car` | Car | `C` | 1 | 3 | float64 | 229,604 | **776,784.88** | 12,364.0 | 1,584.97 |
| `HVG` | HVG | `H` | 3 | 3 | float64 | 106,661 | **51,154.52** | 5,007.6 | 376.87 |
| `PUT` | PUT | `PUT` | 7 | 3 | float64 | 186,707 | **139,821.27** | 68.3 | 0.15 |

- **Zone labels:** read from mapping `NO` (label → 0-based row/col index). Labels are integers; **use
  these as the `tazRelation` `from`/`to` ids** (== `ZONE.NO` == SUMO `taz` id).
- `MATRIXTYPE = 3` = VISUM demand (trip) matrix. `CODE`/`NO` are VISUM matrix identifiers.
- **No vehicle-type or time-period metadata** beyond core name/code is present in the file (no period
  attributes) → interval `begin`/`end` defaults to a full day unless overridden (§4).
- Demand is float (fractional trips); od2trips handles fractional counts. Intrazonal (diagonal) demand
  exists (e.g. Car 1,584.97) — see §4 intrazonal rule (dropped when zone has no spawn/absorb path).

> **Implemented:** `tools/import/gis/omx/adapter.py` reads mapping **`NO`**, emits `interval id` = vType
> per core, and applies zone-access filtering for intrazonal cells (§5.4).

---

## 4. OMX → `tazRelation.xml` rule (ADR-012, Option A)

1. Open with `openmatrix`; read the **named mapping `NO`** → `{label: index}`; invert to an ordered
   `labels[index]` array. **Do not** use positional indices as ids.
2. For each **non-empty** core, emit one `<interval>` whose **`id` is the SUMO vType** for that mode
   (resolved §10-b: interval id == vType, not the core name): `Car→passenger`, `HVG→truck`, `PUT→` a
   configurable PuT vType (default `bus`, §6/§10-a). `begin="0" end="86400"` (no period metadata in
   file; time-slicing via `--timeline` or future time-sliced source — §10-b).
3. For each cell `> 0`: `<tazRelation from="{labels[i]}" to="{labels[j]}" count="{value}"/>`. Skip
   zero/negative cells. Counts kept as given (integer-formatted when integral, else float).
4. **One `od2trips` call per vType** (`--vtype`/`--prefix`, canonical SUMO pattern, §8/§10-b), each
   consuming the per-mode `tazRelation` interval and the per-mode `tazs.xml` (§5/§10-f).
5. **Intrazonal demand — RESOLVED (§10-c): keep when path exists.** Emit diagonal cells (`from == to`)
   when `> 0` **and** the zone has at least one resolvable `tazSource` **and** `tazSink` for that mode.
   Default `emit_intrazonal=true`; optional flag to drop all intrazonal. When the zone has intrazonal
   demand but no spawn/absorb path, drop the diagonal cell with a warning. Degenerate trips (same
   source/sink edge) are acceptable in v1.
   accepted in v1 — tiny share of total demand (Car 0.20%, HVG 0.74%, PUT ~0%).
6. Output validates against `datamode_file.xsd` (ADR-007).

---

## 5. `ZONE` + `CONNECTOR` → `tazs.xml` rule (ADR-014, fail-loud)

### 5.1 `ZONE` (726) — TAZ identity

| Field | Example | Role |
|---|---|---|
| `NO` | `110` | **SUMO `taz` id** (== OMX label; preserve verbatim) |
| `NAME` | `Innenstadt_Zirkel` | diagnostic label |
| `XCOORD`/`YCOORD` | `934762.70 / 6269747.84` | centroid (sphere-Mercator, same frame as `NODE`; §7) — diagnostic only for the connector path |
| `TYPENO` | `0`,`3`,`9` | zone type metadata (dist: `0`=77, `3`=391, `9`=258); not required for the build |
| `SURFACEID` | `1` | polygon surface ref — used only by the GeoJSON polygon fallback, not the connector path |

### 5.2 `CONNECTOR` (5,646) — zone↔node access

| Field | Example | Role |
|---|---|---|
| `ZONENO` | `110` | zone id (FK → `ZONE.NO`) |
| `NODENO` | `105225992` | network node (FK → `NODE.NO` = SUMO node id) |
| `DIRECTION` | `O` / `D` | **`O` → `tazSource`** (trip origin/spawn); **`D` → `tazSink`** (trip destination/absorb) |
| `TSYSSET` | `BIKE,CAR,HGV,WALK` / `PUTW` | permitted systems on the connector → mode filter (§6) |
| `TYPENO` | `0` (road) / `9` (PuT) | connector type (dist: `0`=3,064, `9`=2,566, `4`=12, `2`=2, `1`=2) |
| `WEIGHT(PRT)` | `34` | PrT connector weight (% per zone+direction) — **ignored in v1**; see `specs/assumptions/demand-taz-weighting-v1.md` |
| `WEIGHT(PUT)` | `100` | PuT connector weight — **ignored in v1** (same assumption doc) |
| `T0_TSYS(CAR/HGV/BIKE/PUTW/WALK)` | `364` | per-mode access time (seconds) — informational v1 |
| `LENGTH` | `0.178` | connector length (km) — informational |

`TSYSSET` distribution: `BIKE,CAR,HGV,WALK` (2,955), `PUTW` (2,578), `BIKE,CAR,HGV,PUTW,WALK` (105),
*(empty)* (6), `BIKE,CAR,PUTW,WALK` (2).

### 5.3 Connector → edge resolution (the core rule)

For a PrT (`CAR`/`HGV`) `taz`:

1. Select the zone's connectors whose `TSYSSET` contains a PrT token for the target mode (e.g. `CAR`).
2. **Zone-level direction synthesis (when demand requires a missing side):** if the zone has **no**
   `D` (or `O`) connectors at all for mode M but OMX demand requires inbound (external attraction) or
   outbound (external production) access, synthesize the missing direction from **all** existing
   connectors on the other side (same `NODENO`, same `TSYSSET`); log a warning. Partial success is
   acceptable — some mirrored connectors may still fail the vClass filter.
3. For each such connector, map `NODENO` → SUMO node id (`str(NODENO)`), then resolve **incident
   edges** in `net.xml`:
   - `DIRECTION='O'` → `tazSource` = edges whose **`from` node** is `NODENO` (vehicles depart into the
     network here).
   - `DIRECTION='D'` → `tazSink` = edges whose **`to` node** is `NODENO` (vehicles arrive here).
4. **Edge weights (v1 — uniform):** union all resolved incident edges from qualifying connectors for
   that zone and direction; **deduplicate** by edge id; assign **equal weight** (`1`) to each. Do
   **not** read `WEIGHT(PRT)` / `WEIGHT(PUT)` (provisional business assumption —
   `specs/assumptions/demand-taz-weighting-v1.md`). Connectors whose node yields no usable edge after
   the vClass filter contribute nothing; no renormalization step is required.
5. Emit `<taz id="{ZONE.NO}"> <tazSource id="{edge}" weight="1"/> … <tazSink id="{edge}" weight="1"/>
   </taz>` (or the equivalent simple `edges="…"` form when O/D sets coincide).

### 5.4 Fail-loud (ADR-014, PRD §4)

- OMX zone label ∉ `ZONE.NO` → **error** (cannot happen for this file — set match proven — but enforced).
- A zone with **external** demand in a direction (row sum for production, column sum for attraction,
  excluding the diagonal) but **no** resolvable `tazSource` (outbound) or `tazSink` (inbound) edge
  after synthesis and vClass filtering → **error**, naming the zone and the missing direction.
- **Intrazonal-only** zones with no spawn/absorb path (no `tazSource` **and** no `tazSink` after
  filtering) → **exclude** from `tazs.xml` and **drop** diagonal OMX cells with a warning (do not error).
  Example: Karlsruhe zone `3951` (bike-only CAR connector edges, intrazonal Car/HVG only).
- The **28** zero-demand PuT-only zones (§2.4) → **reported + excluded**, not errored.
- Unmapped `TSYSSET` token on a connector → **reported** (warning), never silently dropped.

**Normative sentence:** If a zone has O (or D) connectors for mode M but no D (or O) connectors at
all, and demand requires that direction, synthesize the missing direction from **all** existing
connectors on the other side (warn). If synthesis still cannot yield any resolvable edges and
**external** demand exists in that direction, error.

---

## 6. Mode mapping (consistent with `import-network-sqlite`) **(confirm)**

Reuse `tools/import/gis/normalize/modes.py` (`DEFAULT_MODE_MAPPING`). OMX cores → SUMO vType/vClass:

| OMX core | VISUM `MODE` | SUMO vType | Connector filter (`TSYSSET` token) | Note |
|---|---|---|---|---|
| `Car` | `C` (CAR) | `passenger` | `CAR` | private car — clean road path |
| `HVG` | `H` (HGV) | `truck` | `HGV` | heavy goods (German *Lastkraftwagen*) |
| `PUT` | `PuT` (BUS,PUTW,TRAIN,TRAM) | — (not injected v1) | `PUTW` | **Out of scope v1** — scenarios 1–2: GTFS for PuT; see `specs/future/demand-pt-scenarios.md` |

- **`PUT` deferred (v1 scenarios 1–2).** PuT demand is served by **GTFS / SUMO PT**, not OMX
  `od2trips`. The `PUT` core is **not imported** in `import-od-demand` v1 (reported as skipped). Rationale:
  PuT is line-conditioned; aggregated PuT OMX is macro input for assignment, not a native SUMO PT
  input — see `specs/future/demand-pt-scenarios.md`.
- The map **MUST be configurable** (`build_options.mode_mapping` / core→vType override) and unmapped
  cores/tokens **reported**, never dropped (AequilibraE pattern; consistent with network import).

---

## 7. CRS / geometry note

- `ZONE.XCOORD/YCOORD` and `CONNECTOR` geometry are in the same **sphere-Mercator** frame as `NODE`
  (`import-network-sqlite` §7). The connector path resolves zones to edges **by node id, not by
  geometry**, so no reprojection is required for the primary path. Reprojection only matters for the
  GeoJSON polygon fallback (§9).
- **Anomaly (1 node):** 1 of 1,387 CAR-connector nodes is in `NODE` but is **not** a `LINK` endpoint
  (no incident edge survived the network build, e.g. all incident directions had empty `TSYSSET`). If a
  demand-bearing zone depends solely on such a node, §5.4 fails loud; otherwise it is reported.

---

## 8. od2trips orchestration (ADR-005, ADR-006)

```
tazs.xml + tazRelation.xml + net.xml → od2trips → trips.xml → (optional) duarouter → routes.xml
```

- Resolve `od2trips`/`duarouter` via `sumolib.checkBinary`; invoke with
  `-n net.xml --taz-files tazs.xml --od-matrix-files/-z tazRelation.xml -o trips.xml` (exact flags in
  design). Save config + capture stdout/stderr to a build log (osmBuild pattern).
- Per-core vType wiring (one interval per core) resolved in design; **(confirm §10-b)**.

---

## 9. CONNECTOR-path decision vs alternatives (ADR-014 extension)

| Option | Approach | Verdict |
|---|---|---|
| **A — primary** | `CONNECTOR.NODENO` → incident **real** net edges as `tazSource`/`tazSink` (this doc) | **Chosen** for Karlsruhe — exact lookup, proven crosswalk |
| B — fallback | Zone **polygons** + `tools/edgesInDistricts.py` against `net.xml` (ADR-014 Option A) | Documented sibling/fallback when `CONNECTOR` absent (e.g. GeoJSON-only); only 468/726 zones have polygons |
| C — rejected | Import `CONNECTOR` as separate `function="connector"` net edges | Rejected; upstream default is `netconvert --visum.no-connectors=true` — connectors are macroscopic, prefer mapping to real edges |

The connector path **extends** ADR-014 (which currently names polygons + `edgesInDistricts` as v1
primary). An ADR-014 note will record that the SQLite `CONNECTOR` path is primary when present.

---

## 10. Open questions (modeller review 2026-06-18)

Resolutions below are from the modeller discussion + measured evidence. Items still flagged **(OPEN)**
need a final call before `/sumo-apply`.

- **(a) `PUT` core handling — RESOLVED (v1: defer).** Scenarios 1–2 (`specs/future/demand-pt-scenarios.md`):
  **do not inject** `PUT` via `od2trips`; PuT via GTFS. Keep `Car`/`HVG` (and other PrT OMX cores).
  The PuT OMX may still be used upstream (assignment, calibration) but not in `import-od-demand` v1.
  Evidence retained: PUT demand = 139,821 trips; 447 `PUTW` connector nodes — relevant for a future PT
  track, not for this change.
- **(b) Mode/time slicing — RESOLVED.** Per the SUMO O/D doc: in `tazRelation` the **`interval id` is
  the vehicle type**, not the time slice (time = `begin`/`end`); the canonical pattern is **one
  `od2trips` call per vType** (`--vtype`/`--prefix`). So **mode → separate vType/calls**, **time →
  multiple `<interval>` (begin/end) or `--timeline`**. This OMX carries **no time dimension** (3
  full-day matrices by mode only), so v1 emits **one full-day interval per mode** (vType as the interval
  id); time-sliced demand (the modeller's "6×10-min per mode" case) is supported by SUMO but requires
  time-sliced source data — future. **Corrects** the earlier "interval id = core name" plan.
- **(c) Intrazonal demand — RESOLVED: keep when path exists.** Modeller decision: emit diagonal OD
  cells in `tazRelation.xml` (`emit_intrazonal=true` default) when the zone has both `tazSource` and
  `tazSink` edges for that mode. Drop diagonal cells with a warning when the zone is intrazonal-only
  and has no car/truck path (Karlsruhe zone `3951`). Measured diagonal totals remain tiny (Car 0.20%,
  HVG 0.74%, PUT ~0%); many intrazonal trips may be degenerate in single-connector zones (source edge ≈
  sink edge). Robust intrazonal routing (min trip length, `--different-source-sink`) deferred.
- **(h) Connector direction synthesis — RESOLVED.** At zone + mode level: if the zone has O (or D)
  connectors for mode M but **no** D (or O) connectors at all, and OMX **external** demand requires
  that direction, synthesize the missing direction from **all** connectors on the other side (warn).
  Fail loud only when **external** demand remains unserved after synthesis. See §5.3–5.4.
- **(d) Connector weighting — RESOLVED (v1: ignore).** **Do not use `WEIGHT(PRT)` / `WEIGHT(PUT)` in
  v1.** Union incident edges from all qualifying connectors per zone+direction; deduplicate; assign
  equal `weight="1"` on each `tazSource`/`tazSink`. Rationale: avoids connector→edge split,
  zero-weight, and renormalization decisions; valid for `od2trips` → `duarouter`. Documented as a
  **provisional business assumption** (`specs/assumptions/demand-taz-weighting-v1.md`); VISUM-faithful
  weight mapping deferred to a future change.
- **(e) `TSYSSET` edge filter — RESOLVED.** Restrict resolved incident edges to those whose `allow`
  includes the target vClass (avoids spawning cars on PuT-only edges).
- **(f) Per-mode tazs — RESOLVED: one `tazs.xml` per mode.** SUMO requires unique `taz` ids and runs
  one `od2trips` per vType, so emit **one taz file per mode** with the *same* zone ids but mode-filtered
  source/sink edges (VISUM supplies per-mode connector `TSYSSET`). Not per-mode ids inside one file.
  This is (e) applied per mode.
- **(g) Polygon fallback / connector inference — RESOLVED: out of scope here.** Confirmed **no missing
  connectors** in the SQLite: every demand-bearing zone has O **and** D connectors (698 zones have CAR
  connectors; the 28 without are the zero-demand external zones, §2.4). So inference is **not needed**
  for the SQLite path. AequilibraE's `connector_creation` / `k_nearest_in_zone` (nodes *within the zone
  polygon* + k-nearest to centroid, per mode) is recorded as the **starting point for the future
  GeoJSON fallback** when connectors are absent — no development in this change.

---

## 11. Sign-off log

*(pending modeller sign-off before `/sumo-apply`.)*

- 2026-06-18 — review pass: (a) **PUT deferred** (scenarios 1–2; GTFS for PuT), (b) interval id = vType +
  one od2trips/vType, (c) **keep intrazonal**, (d) v1 ignores connector weights (uniform; see
  assumptions doc), (e) vClass edge filter, (f) one tazs.xml per mode, (g) connector inference out of
  scope.

---

## 12. Fixture plan (synthetic, compact)

A tiny synthetic OMX (via `openmatrix`) + tiny SQLite (`ZONE`, `CONNECTOR`, reusing the network
fixture's `NODE`/`LINK`) encoding each rule so unit tests don't need the 1.77 MB OMX / 31.8 MB DB:

- 2-core OMX with a named `NO` mapping (e.g. zones `10,20,30`) → tazRelation with **labels from the
  mapping** (not 0/1/2), one interval per core, zero cells skipped, an intrazonal cell emitted.
- OMX whose mapping is missing → falls back to indices **with a reported warning** (or errors —
  resolve in §10).
- zone with O+D CAR connectors at known nodes → `tazSource` on `from`-edges, `tazSink` on `to`-edges,
  **equal weights** (including a connector with `WEIGHT(PRT)=0` to prove the field is ignored).
- zone whose connector `NODENO` has **no incident edge for a direction** + has **external** demand →
  **fail loud**; intrazonal-only zones with no path → excluded + intrazonal OMX cell dropped (warn).
- zone with only `O` (or only `D`) connectors but external attraction (or production) → synthesize
  missing direction from all connectors on the other side (warn).
- PuT-only zero-demand zone → reported + excluded (mirrors the 28 Karlsruhe zones).
- OMX zone label absent from `ZONE` → fail loud (strict alignment).
- unmapped connector `TSYSSET` token → reported, not dropped.

Real Karlsruhe smoke (opt-in): real OMX + real SQLite + real `net.xml` → assert OMX `NO` set ==
`ZONE.NO` set (726); all **external-demand** zones resolve ≥1 `tazSource` and ≥1 `tazSink`; the 28
PuT-only zones excluded; `od2trips` runs and emits a **non-empty** `trips.xml`. Counts recorded below.

### Karlsruhe smoke results (2026-06-22)

End-to-end run: `Visum_3_modes.omx` + `Karlsruhe-sqlite.sqlite3` + `net.xml` from
`import-network-sqlite` via `build_demand_from_visum` (`DemandBuildOptions(run_duarouter=False)`).

| Check | Result |
|---|---|
| OMX `NO` count | **726** |
| `ZONE.NO` count | **726** |
| OMX `NO` == `ZONE.NO` | **TRUE** |
| `tazRelation` relations emitted — `Car` | **229,603** (OMX has 229,604 non-zero; **1** intrazonal dropped: zone `3951`) |
| `tazRelation` relations emitted — `HVG` | **106,660** (OMX has 106,661 non-zero; **1** intrazonal dropped: zone `3951`) |
| `tazs.xml` zones — `passenger` | **587** |
| Zones excluded — `Car` | **139** (28 PuT-only `2000115…2000142`; zone `3951` intrazonal-only/no car path; **110** external mirror zones with zero Car demand in OMX) |
| `od2trips` return code | **0** (`passenger`, `truck`) |
| Trips emitted — `passenger` | **776,792** |
| Trips emitted — `truck` | **51,180** |
| Zone `3951` handling | Intrazonal OMX cells **dropped with warning** (bike-only CAR connector edges) |

**§7 anomaly (1 CAR-connector node not a `LINK` endpoint):** no demand-bearing zone depends solely on
that node; build succeeds without error.
