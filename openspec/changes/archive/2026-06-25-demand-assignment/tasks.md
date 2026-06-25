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

## 6. Karlsruhe reference acceptance

**Change gate (done):** real Karlsruhe inputs → non-empty `assignment/routes.xml` at a scale suitable
for CI and local smoke. **Not a merge gate:** full-day volume or `sumo-gui` on the full model — deferred
until a smaller reference network exists (team decision 2026-06-25).

- [x] 6.1 Produce `assignment/routes.xml` on real Karlsruhe OMX + SQLite + `net.xml` via the
  productized assignment path. **Evidence (2026-06-25):** `reachable_trips` demand rebuild;
  1 h window (`begin=0`, `end=3600`), sorted departures; `duaIterate` iterations 0–1 completed;
  `c:\tmp\karlsruhe\assignment\routes.xml` (~25.8 MB, exit 0). Log:
  `assignment/rebuild-and-duaIterate.log`, `assignment/duaIterate-1h-sorted.log`.
- [ ] 6.2 **Deferred (non-blocking)** — full-day `duarouter` on Karlsruhe (~828k trips, ~1 h).
- [ ] 6.3 **Deferred (non-blocking)** — full-scale `duaIterate` on daily demand (unbenchmarked).
- [ ] 6.4 **Deferred (non-blocking)** — `sumo-gui` smoke on Karlsruhe (`sumocfg` + automated
  `assignment/routes.xml`); prior manual smoke used `sim/routes.xml` only.

## 7. Spec hygiene (before archive)

- [x] 7.1 Update `specs/interfaces.md` with `build_runnable_scenario` contract (`unverified`).
- [x] 7.2 Update `specs/coverage.md` § Current focus — `demand-assignment` apply/complete.
- [x] 7.3 Run `/check-spec demand-assignment` — resolve Blockers. **Audit 2026-06-25:** no Blockers;
  openspec validate fixed (requirement SHALL wording); see session notes below.
