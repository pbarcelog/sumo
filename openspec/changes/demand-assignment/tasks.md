# Tasks — demand-assignment

Spec-first pass: every box below is intentionally unchecked until `/sumo-apply`.

## 1. Workspace layout and manifest

- [x] 1.1 Add `workspace/reference.py` with `ScenarioReferenceLayout` (paths for `sources/`,
  `network/`, `demand/`, `assignment/`, `sim/`).
- [x] 1.2 Implement `build_manifest.py` — SHA-256 fingerprints for OMX, SQLite, `net.xml`; stage
  artifact paths; tool versions; read/compare for invalidation.
- [x] 1.3 Unit tests: manifest round-trip, hash change detection (net-only vs OMX change).

## 2. Assignment orchestration

- [x] 2.1 Add `orchestrate/assignment.py` with `AssignmentOptions` (`method`, `iterations`,
  `begin`, `end`) and `AssignmentResult`.
- [x] 2.2 Implement `duaIterate` invocation via subprocess (`SUMO_HOME/tools/assign/duaIterate.py`);
  comma-separated `-t` for multi-vType trips; logs under `assignment/`.
- [x] 2.3 Implement opt-in `duarouter` path with `--trip-files` comma list (fix `demand.py` bug if
  still used).
- [x] 2.4 Copy/link final `routes.xml` to `assignment/routes.xml`; fail loud on non-zero exit with
  log path.
- [x] 2.5 Unit tests: mock subprocess — verify CLI argv for two trip files (no duplicate `-t`).

## 3. Runnable scenario entry point

- [x] 3.1 Add `orchestrate/scenario.py` — `build_runnable_scenario(omx, sqlite, net, workspace,
  options)` chaining `build_demand_from_visum` + assignment + manifest.
- [x] 3.2 Implement invalidation: net-only → skip od2trips, re-assign; OMX/SQLite change → full
  demand rebuild.
- [x] 3.3 Optional `emit_sumocfg` — minimal `sim/<id>.sumocfg` (begin/end, teleport, net + routes).
- [x] 3.4 Export from `orchestrate/__init__.py`.

## 4. CLI

- [x] 4.1 Add `cli/build_scenario.py` + `cli/__main__.py` — argparse for workspace, omx, sqlite,
  net, assignment options, env-var defaults (`KARLSRUHE_*`).
- [x] 4.2 Document one-line invocation in module docstring (no per-user `build_routes.py`).

## 5. Integration tests

- [x] 5.1 Synthetic fixture: tiny net + OMX/SQLite fixtures → `routes.xml` via `duarouter` (fast CI).
- [x] 5.2 Opt-in Karlsruhe slow test: real OMX + SQLite + `net.xml` → non-empty
  `assignment/routes.xml`.
- [x] 5.3 Invalidation test: mutate net copy → assignment-only rebuild reuses trips.

## 6. Karlsruhe first sim (manual acceptance)

- [ ] 6.1 Run CLI against `c:\tmp\karlsruhe\` (or regenerate workspace) until `assignment/routes.xml`
  exists.
- [ ] 6.2 Launch `sumo-gui -c c:\tmp\karlsruhe\sim\karlsruhe.sumocfg` — confirm sim starts at
  breakpoint 1800s without immediate mass teleport (note counts in session log).

## 7. Spec hygiene (before archive)

- [x] 7.1 Update `specs/interfaces.md` with `build_runnable_scenario` contract (`unverified`).
- [x] 7.2 Update `specs/coverage.md` § Current focus — `demand-assignment` apply/complete.
- [ ] 7.3 Run `/check-spec demand-assignment` — resolve Blockers.
