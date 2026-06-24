# Change: import-od-demand

**Status:** Proposed (spec-only first pass — no implementation, all tasks unchecked)
**PRD:** §1 (OMX + spatial → runnable demand), §2 (OMX format), §4 (fail-loud, determinism, traceability)
**ADRs:** 005 (OD/demand pipeline), 006 (orchestration), 009 (placement), 012 (OMX adapter), 014 (TAZ alignment)
**Epic:** `gis-api-mvp` — Pillar 2 (demand). Unblocks Karlsruhe microsim.
**Depends on:** `import-network-sqlite` (built `net.xml`; ids preserved). **Companion:** `data-inventory.md` (review gate).

## Why

`import-network-sqlite` builds the Karlsruhe road graph but **deliberately omitted `ZONE` and
`CONNECTOR`** (data-inventory §3.6/§3.7) — they belong with the demand, not the network. To run a
microsimulation, SUMO needs three layers, not one file: the network (`net.xml`, done), **TAZ
definitions** (`tazs.xml`: zone → network edges for trip spawn/absorption), and the **OD matrix**
(`tazRelation.xml`: trip counts between zone ids). `od2trips` requires all three; the OMX matrix
carries **no** connector/access information. This change closes the gap end-to-end and unblocks the
Karlsruhe microsim.

It is **data-first**: the contract is anchored to the real `Visum_3_modes.omx` (726×726, cores `Car`,
`HVG`, `PUT`) and the real `Karlsruhe-sqlite.sqlite3` `ZONE` (726 rows) / `CONNECTOR` (5,646 rows). The
crosswalk is already **proven**: the OMX `NO` mapping equals `ZONE.NO` exactly (726/726, zero diffs),
every connector node exists in `NODE`, and CAR connector nodes resolve to `LINK` endpoints that became
real SUMO edges (data-inventory §2). This is the decisive advantage of the SQLite `CONNECTOR` path over
the GeoJSON polygon + `edgesInDistricts` path: the macroscopic access model already names the exact
nodes, so `tazSource`/`tazSink` edge assignment is a lookup, not a spatial guess.

## What Changes

- **ADD** `od-import-demand` capability: OMX matrix + VISUM `ZONE`/`CONNECTOR` → `tazRelation.xml` +
  `tazs.xml`, then orchestrate `od2trips` (+ optionally `duarouter`).
- **OMX → `tazRelation.xml` (ADR-012):** read all non-empty cores via `openmatrix`; use the OMX
  **named mapping** (`NO`) for zone labels — **not** positional indices — emitting one `tazRelation`
  `interval` per matrix (`Car`, `HVG`, `PUT`). This corrects the current `omx/adapter.py` skeleton,
  which calls `f.mapping(matrix_name)` (the mapping is named `NO`, so it silently falls back to 0-based
  indices) and labels intervals by `vType` instead of matrix.
- **`ZONE` + `CONNECTOR` → `tazs.xml` (ADR-014):** for each zone, resolve `CONNECTOR.NODENO` to the
  built network edges incident at that node (`NODE.NO` is the SUMO node id; `LINK.NO`/`-NO` the edge
  ids — `import-network-sqlite` preserved both). `DIRECTION='O'` connectors → `tazSource` (edges
  **leaving** the node); `DIRECTION='D'` → `tazSink` (edges **entering** the node). **v1:** union
  qualifying connector edges with **uniform weights**; `WEIGHT(PRT)` ignored (see
  `specs/assumptions/demand-taz-weighting-v1.md`).
- **Strict zone-id alignment (ADR-014, fail-loud):** OMX zone labels ⊆ `ZONE.NO` ⊆ `tazs` ids; fail
  loud on any unknown zone, and fail loud when a zone that carries demand has no resolvable connector
  edge. The 28 high-numbered zones (`2000115`–`2000142`) that have **only PuT connectors and zero
  demand** in every core are reported and excluded, not errored (data-inventory §2.4).
- **Mode mapping consistent with `import-network-sqlite`:** reuse `normalize/modes.py`
  (`CAR→passenger`, `HGV→truck`, …); map OMX cores `Car→passenger`, `HVG→truck`, and report any
  unmapped core. `PUT` road-loading is an **open question** (its connectors point to PuT stop nodes, not
  road edges) — see data-inventory §6.
- **Library entry point (ADR-009):** `(omx_path, sqlite_path, net_xml, build_options) → tazRelation.xml
  + tazs.xml + build report`. No new HTTP surface in this change.
- **Orchestration hook (ADR-006):** feed `od2trips` (and optionally `duarouter`) following the
  existing `orchestrate/pipeline.py` pattern, via `sumolib.checkBinary`.
- **Validated against real data:** synthetic OMX/SQLite fixtures for each rule + an opt-in Karlsruhe
  smoke (OMX zones match `ZONE`; connectors resolve to edges; `od2trips` emits a non-empty `trips.xml`).

## Capabilities

### New Capabilities

- `od-import-demand`: OMX core → `tazRelation` interval translation (named-mapping zone labels,
  per-core intervals, mode/vType assignment, unmapped-core reporting); VISUM `ZONE`/`CONNECTOR` →
  `tazs.xml` with `tazSource`/`tazSink` edges resolved from connector `NODENO` against the built
  network (O→source, D→sink, uniform edge weights in v1); strict OMX↔`ZONE`↔`tazs` id alignment with
  fail-loud on unknown zones and demand-bearing zones lacking connector edges; `od2trips` (and optional
  `duarouter`) orchestration; build-report/log retention.

### Modified Capabilities

- *(none — `omx-adapter` and `scenario-orchestration` are defined in the **unarchived** `gis-api-mvp`
  change, so there is no archived capability under `openspec/specs/` to delta. `od-import-demand`
  supersedes the OMX skeleton behavior; the corrections are stated as new requirements here.)*

## Impact

- **Code (writable roots only, ADR-009):** `tools/import/gis/omx/**` (named-mapping reader, per-core
  intervals, mode/vType), a new `tools/import/gis/normalize/` zone/connector → tazs module, and
  `tools/import/gis/orchestrate/**` (od2trips/duarouter hook). Reuses `normalize/modes.py`. No `src/`
  or upstream `tools/` edits.
- **Tests:** `tests/tools/import/gis/demand/**` — synthetic OMX (`openmatrix`) + tiny-SQLite fixtures
  per rule; opt-in real-DB + real-OMX Karlsruhe smoke.
- **Specs:** `specs/interfaces.md` OMX and tazRelation/TAZ rows move toward `partial`;
  `specs/coverage.md` notes the demand path; an ADR-014 note records that the SQLite `CONNECTOR` path
  extends the v1 polygon+`edgesInDistricts` derivation.
- **Anchor data:** `C:\Users\Pablo Barceló\Downloads\Karlsruhe\Visum_3_modes.omx` and
  `…\Karlsruhe-sqlite.sqlite3`.
- **Dependencies:** `openmatrix` (already present), stdlib `sqlite3`, `sumolib.checkBinary` for
  `od2trips`/`duarouter`.

## Out of Scope

- Control plans / signal timings (`import-control-plan`).
- Full `sumo` microsim run / calibration of the produced demand.
- **GeoJSON-only zone path** — documented as a sibling/fallback (zone polygons + `edgesInDistricts`,
  ADR-014 Option A); the SQLite `CONNECTOR` path is **primary** for Karlsruhe.
- Importing `CONNECTOR` rows as separate `function="connector"` network edges — the default is ADR-014
  edge assignment to **real** net edges (upstream `netconvert --visum.no-connectors=true`); the
  decision is recorded in `design.md`.
- `PUT` (public-transport) OMX injection — **out of scope v1**; PrT-only demand per
  [`specs/future/demand-pt-scenarios.md`](../../../specs/future/demand-pt-scenarios.md) scenarios 1–2
  (private OD + GTFS for PuT; discard `PUT` slice for SUMO injection).
- HTTP API surface / job orchestration / workspace status (later).
