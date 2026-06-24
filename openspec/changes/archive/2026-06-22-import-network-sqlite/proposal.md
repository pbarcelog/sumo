# Change: import-network-sqlite

**Status:** Proposed
**PRD:** §2 (formats), §4 (quality/CRS)
**ADRs:** 006 (orchestration), 009 (placement), 011 (normalization), 013 (SQLite role)
**Epic:** `gis-api-mvp` — Pillar 1 (network import), SQLite path.
**Sibling:** `import-network-geojson` (same VISUM source, leaner export). **Companion:** `data-inventory.md` (review gate).

## Why

`gis-api-mvp` must build a SUMO network from a VISUM **SQLite** export — the simpler, data-richer
sibling of the GeoJSON path. Following the gis-api-mvp lesson (data-first, anchored to a real file),
this change is grounded in the actual Karlsruhe DB (`Karlsruhe-sqlite.sqlite3`, 31.8 MB), whose field
inventory and translation rules are fixed in `data-inventory.md` **before** any code.

The SQLite export resolves the central defect the GeoJSON change could only paper over: GeoJSON left
1,056 public-transport-only directions at `V0PRT=0` and required a hand-tuned `LC` fallback table for
their speed. SQLite carries **per-link-type, per-mode speeds** (`LINKTYPE.VMAX_PRTSYS(*)` /
`VDEF_PUTSYS(*)`) and **PuT travel times** (`LINK.T_PUTSYS(*)`). Measured over the real DB, this yields
a **positive speed for all 19,401 transport-bearing directed links with zero unresolved and no epsilon
hack** — the decisive advantage of the SQLite source.

## What Changes

- **ADD** `network-import-sqlite` capability: read a VISUM SQLite network (`NETWORK`, `NODE`, `LINK`,
  `LINKTYPE`, `TSYS`, optional `LINKPOLY`) → build a SUMO `net.xml` via `netconvert`.
- **ADD** a **library-level entry point** (DB path + build options in, `net.xml` + build report out).
  No HTTP/jobs in this change — the FastAPI surface wraps it later.
- **Directed-row handling:** `LINK` stores each direction as its own row sharing `NO`. Group by `NO`,
  assign AB→`NO` / BA→`-NO` by `(FROMNODENO, TONODENO)` ordering; skip+log directions with empty
  `TSYSSET` (4,089 rows; 843 links fully skipped).
- **Mode → vClass** from `TSYSSET` (`CAR→passenger`, `HGV→truck`, `BIKE→bicycle`, `BUS→bus`,
  `TRAM→tram`, `TRAIN→rail_urban`, `PUTW→pedestrian`, `WALK→pedestrian`). The map is **configurable**
  (`build_options.mode_mapping`) and **unmapped TSys tokens are reported, never silently dropped**
  (AequilibraE pattern; consistent with `import-network-geojson`).
- **Per-mode speed from `LINKTYPE`:** edge `speed` ceiling = max permitted-mode speed (PrT `VMAX_PRTSYS`,
  PuT `VDEF_PUTSYS`, plus `V0PRT` when > 0), converted km/h→m/s. Every allowed mode whose per-mode speed
  is below the ceiling gets an edge-`type` `<restriction vClass=… speed=…/>`, **never** a lane split.
  PuT-only links
  (`V0PRT=0`) get a real positive speed from `VDEF_PUTSYS` — **no fallback table, no epsilon**.
- **Identity preserved:** VISUM `NO` becomes the SUMO node id and signed edge id verbatim.
- **CRS:** source is projected **Sphere_Mercator** (per `NETWORK.PROJECTIONDEFINITION`), not WGS84.
  Reproject with pyproj to the target network CRS (default EPSG:25832, UTM 32N) and feed cartesian
  coords to `netconvert`; log resolved source WKT + target EPSG. No silent reprojection (ADR-011).
- **Lanes:** `LINK.NUMLANES → numLanes`. Per-lane `allow` is **evaluated and deferred** — measured data
  shows **no** dedicated-PT-lane on any shared corridor (0 mixed-`TSYSSET` lane sets).
- **Control plan stand-in:** `netconvert --tls.guess`; real `CONTROLTYPE`/`SIGNALCONTROL` import is
  deferred to `import-control-plan`.

## Capabilities

### New Capabilities

- `network-import-sqlite`: VISUM SQLite table discovery and validation, directed-link normalization
  (AB/BA from paired rows), mode→vClass permission translation with unmapped-token reporting,
  `LINKTYPE`-driven per-mode speed resolution (positive speed for PuT-only links; per-mode restrictions),
  CRS reprojection from the embedded WKT, `LINKPOLY` geometry reconstruction, plain-XML emit + `netconvert`
  build to `net.xml`, and build-report/log retention.

### Modified Capabilities

- *(none — no archived capabilities yet; `network-import-sqlite` is a new sibling of the unarchived
  `import-network-geojson` change.)*

## Impact

- **Code:** `tools/import/gis/normalize/**` (SQLite reader, CRS reprojection, mode/speed translation)
  and `tools/import/gis/orchestrate/**` (plain-XML emit + netconvert build) — writable roots only
  (ADR-009). No HTTP, no `src/`/`tools/` edits.
- **Tests:** `tests/tools/import/gis/network/**` — synthetic tiny-SQLite fixtures + opt-in real-DB smoke
  against `Karlsruhe-sqlite.sqlite3`.
- **Specs:** `specs/interfaces.md` network/normalization rows move toward `partial`; `specs/coverage.md`
  notes the SQLite network path.
- **Anchor data:** `C:\Users\Pablo Barceló\Downloads\Karlsruhe\Karlsruhe-sqlite.sqlite3`.
- **Dependencies:** `geopandas`, `pyogrio`, `pyproj`, stdlib `sqlite3` (already in API requirements);
  SUMO `netconvert` via `sumolib.checkBinary`.

## Out of Scope

- Zones/TAZ (`ZONE`, surface polygons), connectors (`CONNECTOR`), and OD demand — deferred to TAZ /
  `import-od-demand` (ADR-014); OMX via ADR-012.
- Public-transport service: stops, lines, line-routes, timetables, vehicle journeys (`STOP`, `LINE`,
  `LINEROUTE`, `TIMEPROFILE`, `VEHJOURNEY*`) — `import-gtfs` / PT phase.
- HTTP API surface, job orchestration, workspace status.
- Real signal-timing / control-plan import (`import-control-plan`).
- Per-lane `allow` modelling and lane widths (deferred — no supporting data in this export).
- Turns / lane-turns (`TURN`, `LANETURN`) beyond what `netconvert` infers.
