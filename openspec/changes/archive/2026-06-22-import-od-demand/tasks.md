# Tasks — import-od-demand

Data-first order (AequilibraE rhythm): inventory & fixtures **before** code; real OMX + DB smoke
**before** done. Do not check a box without evidence. Translation rules are normative in
`data-inventory.md`. **Spec-only first pass: every box below is intentionally unchecked.**

## 0. Review gate (blocking)

- [x] 0.1 Modeller signs off `data-inventory.md` §11. **Resolved:** (a) PUT deferred v1; (c) keep
  intrazonal; (d) uniform weights (`specs/assumptions/demand-taz-weighting-v1.md`). Demand scenarios:
  `specs/future/demand-pt-scenarios.md`. (Confirmed in implementation session 2026-06-22.)

## 1. Source inventory & fixtures

- [x] 1.1 Confirm the OMX inventory in `data-inventory.md` §3 against the real file (cores `Car`/`HVG`/
  `PUT`, `SHAPE [726 726]`, mapping `NO` 110…2,000,142, totals/non-zero/diag). (Pre-confirmed at propose.)
- [x] 1.2 Confirm the `ZONE`/`CONNECTOR` inventory §5 and the crosswalk §2 against the real DB (726
  zones, 5,646 connectors = 2,823 O + 2,823 D, OMX `NO` == `ZONE.NO`, all connector nodes ∈ `NODE`).
- [x] 1.3 Build a synthetic OMX fixture (`openmatrix`) with a named `NO` mapping (labels ≠ 0-based),
  ≥2 cores, zero cells, and an intrazonal cell. (`tests/tools/import/gis/demand/fixtures.py`)
- [x] 1.4 Build a synthetic SQLite fixture (`ZONE`, `CONNECTOR`) + a tiny `net.xml` whose node ids match
  connector `NODENO`: zone with O+D CAR connectors (including one with `WEIGHT(PRT)=0`), a demand zone
  whose connector node has no incident edge, a PuT-only zero-demand zone, an unmapped-`TSYSSET`
  connector.
- [x] 1.5 Add an OMX-zone-not-in-`ZONE` fixture and a missing-OMX-mapping fixture (fail-loud / report).

## 2. OMX → tazRelation (`omx/`)

- [x] 2.1 Fix `omx/adapter.py` to read the **named mapping** (`NO`) → `labels[index]`; stop using
  positional indices; emit **one interval per non-empty core** (interval `id` = vType per §10-b).
- [x] 2.2 Map each core to a vType (`Car→passenger`, `HVG→truck`) via configurable mapping; report
  unmapped cores; apply `skip_put` (default true).
- [x] 2.3 Emit `<tazRelation from to count>` for cells > 0; keep intrazonal by default (`emit_intrazonal`
  flag); format integral counts as ints. Validate against `datamode_file.xsd`.

## 3. ZONE/CONNECTOR → tazs (`normalize/visum_zones.py`)

- [x] 3.1 Read `ZONE` (id=`NO`) and `CONNECTOR` (`ZONENO`, `NODENO`, `DIRECTION`, `TSYSSET`); reuse
  `normalize/modes.py` for token→vClass. Do **not** read `WEIGHT(PRT)` in v1.
- [x] 3.2 Load `net.xml` via `sumolib.net.readNet`; index edges by `from`/`to` node id.
- [x] 3.3 Resolve connector `NODENO` → incident edges: `O`→`tazSource` (out-edges), `D`→`tazSink`
  (in-edges); restrict to edges that `allow` the target vClass (§10-e).
- [x] 3.4 Union and deduplicate resolved edges per zone+direction; assign equal weight (`1`) to each
  `tazSource`/`tazSink` entry (`specs/assumptions/demand-taz-weighting-v1.md`).
- [x] 3.5 Emit `tazs.xml` (`<taz id><tazSource/><tazSink/></taz>`); report excluded zones + unmapped
  tokens.

## 4. Zone validation & fail-loud (`omx/validate.py`)

- [x] 4.1 Extend strict alignment: OMX `NO` labels ⊆ `ZONE.NO`; fail loud naming unknown zones.
- [x] 4.2 Fail loud when a zone with **external** demand resolves to no `tazSource` or no `tazSink`
  (name zone + direction); intrazonal-only no-path zones excluded with warning.
- [x] 4.3 Report + exclude (not error) zero-demand PuT-only zones (the 28 `2000115…2000142`).

## 5. od2trips orchestration hook (`orchestrate/demand.py`)

- [x] 5.1 `build_demand_from_visum(omx, sqlite, net_xml, out_dir, options) → DemandBuildResult`
  (library entry point, ADR-009).
- [x] 5.2 Resolve `od2trips` via `sumolib.checkBinary`; invoke with `tazs.xml` +
  `tazRelation.xml` → `trips.xml`; per-core vType wiring; save config + log (osmBuild pattern).
- [x] 5.3 Optional `duarouter` → `routes.xml`; surface non-zero return codes with log references.
- [x] 5.4 Populate `DemandBuildResult`: per-core counts, excluded zones, unmapped cores/tokens, return
  codes, artifact paths.

## 6. Unit tests (synthetic fixtures)

- [x] 6.1 `test_omx_mapping` — labels from `NO` mapping (not 0-based); missing-mapping handled.
- [x] 6.2 `test_intervals` — one interval per core; zero cells skipped; intrazonal kept/dropped by flag.
- [x] 6.3 `test_core_vtype` — `Car→passenger`, `HVG→truck`, `PUT` skipped with report; unmapped core
  reported.
- [x] 6.4 `test_connector_resolve` — O→tazSource (out-edges), D→tazSink (in-edges); vClass restriction.
- [x] 6.5 `test_uniform_taz_weights` — all `tazSource`/`tazSink` weights equal; `WEIGHT(PRT)=0`
  connector edges included same as others.
- [x] 6.6 `test_alignment` — exact set match passes; unknown OMX zone fails loud.
- [x] 6.7 `test_fail_loud` — external-demand zone with no source/sink edge errors; intrazonal-only
  no-path zone excluded; PuT-only zero-demand zone excluded; connector-direction synthesis; unmapped
  `TSYSSET` token reported.
- [x] 6.8 `test_determinism` — two runs on identical inputs yield byte-identical `tazRelation.xml` and
  `tazs.xml` (stable sort of intervals/relations/edges).

## 7. Real Karlsruhe smoke (opt-in, blocking for done)

- [x] 7.1 Real `Visum_3_modes.omx` + `Karlsruhe-sqlite.sqlite3` + `net.xml` → `tazRelation.xml` +
  `tazs.xml` + `trips.xml` (verified 2026-06-22; zone `3951` intrazonal dropped with warning).
- [x] 7.2 Assert OMX `NO` set == `ZONE.NO` set (726); per-core relation counts match §3 (`Car`
  229,603 emitted after zone `3951` intrazonal drop; `HVG` 106,660).
- [x] 7.3 Assert every **external-demand** zone resolves ≥1 `tazSource` and ≥1 `tazSink`; the 28
  PuT-only zones excluded; zone `3951` excluded with warning; §7 node anomaly non-blocking.
- [x] 7.4 Run `od2trips` (via `sumolib.checkBinary`, eclipse-sumo) → **non-empty** `trips.xml`; record
  trip count and return code. (776,792 passenger + 51,180 truck trips.)
- [x] 7.5 Record results (per-core counts, excluded zones, trips produced) in `data-inventory.md` §12.

## 8. Spec hygiene & verification

- [x] 8.1 Update `specs/interfaces.md` — OMX and tazRelation/TAZ rows toward `partial` (demand path).
- [x] 8.2 Update `specs/coverage.md` — demand import (OMX + ZONE/CONNECTOR) path.
- [x] 8.3 Amend **ADR-014** to add the SQLite `CONNECTOR` → real-net-edge derivation as a formal option
  (primary when `CONNECTOR` is present; polygons + `edgesInDistricts` as fallback), with rationale from
  `data-inventory §9`, and update `specs/adr-registry.md` if the decision/primary path shifts (per
  `openspec/config.yaml`). Not a deferred note.
- [x] 8.4 Reconcile with `gis-api-mvp`: record that `od-import-demand`'s OMX requirements (named
  mapping, per-core intervals) **supersede** the `omx-adapter` skeleton spec, so the two in-flight
  changes do not archive contradictory OMX-adapter behavior. (`gis-api-mvp/specs/omx-adapter/spec.md`
  supersession note; ADR-012 amendment; `interfaces.md` reconciliation log.)
- [x] 8.5 Run focused pytest (`tests/tools/import/gis/demand/`). (17 passed incl. Karlsruhe smoke.)
- [x] 8.6 Run `openspec validate import-od-demand` and resolve issues.
- [x] 8.7 Reference `specs/assumptions/demand-taz-weighting-v1.md` from ADR-014 amendment note (v1
  uniform weights; VISUM weight mapping deferred).
