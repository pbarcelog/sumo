# Tasks — import-network-geojson

Data-first order (AequilibraE rhythm): inventory & fixtures **before** code; real-file smoke
**before** done. Do not check a box without evidence. Translation rules are normative in
`data-inventory.md`.

## 0. Review gate (blocking)

- [ ] 0.1 Modeller signs off `data-inventory.md`: mode→vClass map (§4), speed fallbacks (§5),
  `TRAIN→rail` vs `rail_urban`, separate-edge vs shared-lane decision.

## 1. Source inventory & fixtures

- [ ] 1.1 Confirm field inventory in `data-inventory.md` against `node.geojson` / `link.geojson`.
- [ ] 1.2 Add compact synthetic `node`/`link` GeoJSON fixtures: bidirectional car link, one-way link
  (empty `R_TSYSSET`), PuT-only `0km/h` link, mixed `LC`, multi-vertex geometry, duplicate coords.
- [ ] 1.3 Add a malformed-input fixture (unparseable GeoJSON) and a missing/ambiguous-CRS fixture.
- [ ] 1.4 Document expected edge/node counts for the real Karlsruhe export in `data-inventory.md`.

## 2. Reader & normalization (`normalize/`)

- [ ] 2.1 Read `node.geojson` → node records (id=`NO`, geometry x/y); ignore assignment metadata.
- [ ] 2.2 Read `link.geojson` → directional edge records (AB + `R_`), preserving `NO`/`-NO` ids.
- [ ] 2.3 Implement `modes.py`: `TSYSSET` token → `vClass` per `data-inventory.md` §4.
- [ ] 2.4 Implement `speed.py`: parse `V0PRT` km/h→m/s, apply `LC` fallback for `0km/h`, log each.
- [ ] 2.5 Implement direction rule: skip+log empty-`TSYSSET` directions; emit reverse from `R_*`.
- [ ] 2.6 Assign edge `type` from `LC` (fallback `TYPENO`); carry geometry shape.

## 3. Plain-XML emit & netconvert build (`orchestrate/`)

- [ ] 3.1 Write SUMO plain XML (`*.nod.xml`, `*.edg.xml`) from normalized records.
- [ ] 3.2 Resolve `netconvert` via `sumolib.checkBinary`; build with `--proj.utm` and `--tls.guess`.
- [ ] 3.3 Save `.netccfg` and capture stdout/stderr to a build log (osmBuild pattern, ADR-006).
- [ ] 3.4 Produce `NetworkBuildResult`: `net.xml` path, resolved EPSG, counts, substitutions, skips.

## 4. Fail-loud behavior

- [ ] 4.1 Explicit errors on unreadable GeoJSON and on unresolved CRS (no silent drops).
- [ ] 4.2 Surface non-zero `netconvert` exit with logs referenced in the result.

## 5. Unit tests (synthetic fixtures)

- [ ] 5.1 `test_modes` — TSYSSET→vClass incl. PuT-only excludes `passenger`.
- [ ] 5.2 `test_speed` — km/h→m/s and `0km/h`→`LC` fallback with log entry.
- [ ] 5.3 `test_direction` — bidirectional vs one-way edge creation.
- [ ] 5.4 `test_build` — fixtures → plain XML → `netconvert` → loadable `net.xml`; assert no
  zero-speed edge and PuT-only edge `allow` has no `passenger`.
- [ ] 5.5 `test_failures` — malformed GeoJSON and CRS errors raise explicitly.

## 6. Real Karlsruhe smoke (opt-in, blocking for done)

- [ ] 6.1 Import real `node.geojson` + `link.geojson` → `net.xml`.
- [ ] 6.2 Assert node/edge counts within documented ranges; **zero zero-speed edges**.
- [ ] 6.3 Assert sampled PuT-only links (e.g. `NO=3118`) became edges that disallow `passenger`.
- [ ] 6.4 Load produced `net.xml` with `netconvert`/`sumo` (no errors); record resolved EPSG.
- [ ] 6.5 Record counts, speed substitutions, and skipped directions in `data-inventory.md`.

## 7. Spec hygiene & verification

- [ ] 7.1 Update `specs/interfaces.md` network/normalization rows toward `partial`.
- [ ] 7.2 Update `specs/coverage.md` (Phase 1 — network import in progress).
- [ ] 7.3 Run focused pytest (`tests/tools/import/gis/network/`).
- [ ] 7.4 Run `openspec validate import-network-geojson` and resolve issues.
