# Tasks — import-network-sqlite

Data-first order (AequilibraE rhythm): inventory & fixtures **before** code; real-DB smoke **before**
done. Do not check a box without evidence. Translation rules are normative in `data-inventory.md`.

## 0. Review gate (blocking)

- [x] 0.1 Modeller signed off `data-inventory.md` §11 (all six decisions resolved 2026-06-18):
  `TRAIN→rail_urban` (§4); restriction scope = every allowed `vClass` below the ceiling (§5); per-lane `allow` and
  `LANE.WIDTH` deferred (§8); CRS = reproject-in-Python to EPSG:25832 (§7); direction sign by
  `(FROMNODENO, TONODENO)` sort (§6); low speeds kept with a motorized-edge coherence log (§5).

## 1. Source inventory & fixtures

- [x] 1.1 Confirm the field inventory in `data-inventory.md` against the real DB (tables, columns,
  counts, CRS WKT, id ranges).
- [x] 1.2 Build a compact synthetic SQLite fixture (`NETWORK`, `NODE`, `LINK`, `LINKTYPE`, `TSYS`,
  optional `LINKPOLY`) encoding: bidirectional car link, one-way link (BA `TSYSSET` empty), fully
  closed link (both empty), PuT-only `V0PRT=0` link (`TYPENO=8`), mixed-speed link (bike < car),
  `LINKPOLY`-geometry link, unmapped-TSys-token link. (`tests/.../network/fixtures.py`)
- [x] 1.3 Add a CRS fixture with a sphere-Mercator `PROJECTIONDEFINITION`, and a missing-CRS fixture.
- [x] 1.4 Add a malformed / non-SQLite input fixture and a missing-required-table fixture.
- [x] 1.5 Document expected counts/ranges for the real Karlsruhe DB in `data-inventory.md` (§1, §12).

## 2. Reader & normalization (`normalize/`)

- [x] 2.1 Discover/validate tables: require `NETWORK`/`NODE`/`LINK`/`LINKTYPE`/`TSYS`; optional
  `LINKPOLY`; report PT/turn/fare/zone tables as deferred. (`normalize/visum_sqlite.py:discover_tables`)
- [x] 2.2 Read `NODE` → node records (id=`NO`, x/y); read `LINK` → directed rows; read `LINKTYPE`/`TSYS`
  lookups.
- [x] 2.3 Implement CRS reprojection: parse `NETWORK.PROJECTIONDEFINITION` WKT, reproject coords to
  target CRS (default EPSG:25832) via pyproj; fail loud on missing/invalid CRS; log source WKT + target
  EPSG. (`normalize/visum_sqlite.py:_make_transformer`)
- [x] 2.4 Implement directed-row pairing: group by `NO`, sort `(FROMNODENO,TONODENO)`, AB=`NO`/BA=`-NO`;
  skip+log empty-`TSYSSET` directions (data-inventory §6).
- [x] 2.5 Implement `modes.py`: `TSYSSET` token → `vClass` via configurable mapping; report unmapped
  tokens (data-inventory §4).
- [x] 2.6 Implement `speed.py`: join `LINKTYPE`; ceiling = max permitted-mode speed (`VMAX_PRTSYS`/
  `VDEF_PUTSYS` + `V0PRT>0`), km/h→m/s; emit `<restriction>` for every allowed `vClass` whose per-mode
  speed is below the ceiling; keep low speeds (no floor) but log a coherence warning when a low ceiling (≤ 5 km/h,
  configurable) lands on a motorized-allowed edge; log all decisions (data-inventory §5). (Cross-check
  against `LENGTH/T_PUTSYS` left as a future diagnostic.)
- [x] 2.7 Reconstruct geometry from `NODE` + ordered `LINKPOLY` vertices (reversed for BA); assign
  `type` from `TYPENO`; map `NUMLANES` → `numLanes` (data-inventory §7/§8).

## 3. Plain-XML emit & netconvert build (`orchestrate/`)

- [x] 3.1 Write SUMO plain XML (`*.nod.xml`, `*.edg.xml`, `*.typ.xml` with restrictions) from
  normalized records in projected cartesian coordinates. (`orchestrate/netbuild.py:write_plain_xml`)
- [x] 3.2 Resolve `netconvert` via `sumolib.checkBinary`; build **without** netconvert reprojection;
  add `--tls.guess`. (Verified via `pip install eclipse-sumo` 1.27.0 — `test_build_produces_loadable_net`.)
- [x] 3.3 Save `.netccfg` and capture stdout/stderr to a build log (osmBuild pattern, ADR-006).
- [x] 3.4 Produce `NetworkBuildResult`: `net.xml` path, source WKT + target EPSG, counts, skipped
  directions, unmapped tokens, speed/restriction decisions.

## 4. Fail-loud behavior

- [x] 4.1 Explicit errors on unreadable DB, missing required table, and missing/invalid CRS (no silent
  drops). (`VisumSQLiteError`; covered by `test_failures`/`test_missing_crs_raises`.)
- [x] 4.2 Surface non-zero `netconvert` exit with logs referenced in the result.

## 5. Unit tests (synthetic fixtures)

- [x] 5.1 `test_discovery` — required-table presence and deferred-table reporting; missing-table error.
- [x] 5.2 `test_direction` — bidirectional vs one-way vs fully-closed; AB/BA sign assignment.
- [x] 5.3 `test_modes` — `TSYSSET`→`vClass` incl. PuT-only excludes `passenger`; unmapped-token report.
- [x] 5.4 `test_speed` — `LINKTYPE` ceiling, PuT-only positive speed (no fallback/epsilon), a
  `<restriction>` for every allowed mode below the ceiling, and the low-ceiling-on-motorized coherence
  warning.
- [x] 5.5 `test_crs` — sphere-Mercator reprojected + logged; missing-CRS raises.
- [x] 5.6 `test_geometry` — `LINKPOLY` vertices preserved and reversed for BA.
- [x] 5.7 `test_build` — fixture → plain XML → `netconvert` → loadable `net.xml`; no zero-speed edge;
  PuT-only edge `allow` has no `passenger`. (`test_build_produces_loadable_net`; eclipse-sumo 1.27.0.)
- [x] 5.8 `test_failures` — unreadable/non-SQLite input raises explicitly.

## 6. Real Karlsruhe smoke (opt-in, blocking for done)

- [x] 6.1 Import the real `Karlsruhe-sqlite.sqlite3` → `net.xml`. (`test_real_karlsruhe_build_loads`;
  eclipse-sumo 1.27.0.)
- [x] 6.2 Assert node/edge counts within documented ranges; **zero zero-speed edges**; fully-skipped
  directions logged. (Real run: 8,432 nodes / 19,401 edges / 4,089 skipped / 0 zero-speed —
  data-inventory §12; `test_real_karlsruhe_normalization`.)
- [x] 6.3 Assert sampled PuT-only edge (e.g. `NO=3118`) disallows `passenger` and has positive speed.
- [x] 6.4 Load produced `net.xml` with `netconvert`/`sumo` (no errors); record resolved source WKT +
  target EPSG. (`test_real_karlsruhe_build_loads`: `sumolib.net.readNet` loads Karlsruhe `net.xml`,
  all edge speeds > 0; source `Sphere_Mercator` WKT, target `EPSG:25832`.)
- [x] 6.5 Record counts, skipped directions, unmapped tokens, and speed decisions in `data-inventory.md`
  (§12).

## 7. Spec hygiene & verification

- [x] 7.1 Update `specs/interfaces.md` network/normalization rows toward `partial` (SQLite path).
- [x] 7.2 Update `specs/coverage.md` (network import — SQLite path).
- [x] 7.3 Run focused pytest (`tests/tools/import/gis/network/`). (23 passed, 0 skipped.)
- [x] 7.4 Run `openspec validate import-network-sqlite` and resolve issues.
