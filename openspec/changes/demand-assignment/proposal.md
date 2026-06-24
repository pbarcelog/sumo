# Change: demand-assignment

**Status:** Proposed (spec-first — no implementation)
**PRD:** §1 (runnable scenarios), §2 (scenario build: od2trips + assignment), §4 (determinism, fail-loud, traceability)
**ADRs:** 005 (OD/demand pipeline), 006 (orchestration), 009 (placement), 015 (workspace)
**Epic:** `gis-api-mvp` — Pillar 2 completion (demand → routes). Unblocks Karlsruhe first microsim.
**Depends on:** `import-od-demand` (archived), `import-network-sqlite` (archived). **Companion:** Karlsruhe workspace at `c:\tmp\karlsruhe\`.

## Why

`import-od-demand` delivers `tazs`, `tazRelation`, and `trips` but **stops before assignment**. The
Karlsruhe reference run has ~828k trips and no `routes.xml`; users currently wire `duarouter` or
`duaIterate` by hand (and the existing `run_duarouter` hook passes `-t` twice, which is invalid).
PRD §1 promises **runnable simulation scenarios** — network plus demand **plus routes** — without
manual `PYTHONPATH` scripts. This change productizes stage 2 (assignment) and a stable workspace layout
so the first Karlsruhe microsim can run immediately after apply.

## What Changes

- **ADD** `demand-assignment` capability: one library entry point from OMX + VISUM SQLite + `net.xml` →
  staged demand artifacts **and** `routes.xml`, with **dynamic user assignment (`duaIterate`) as the v1
  default** and single-pass `duarouter` as an explicit opt-in.
- **FIX** multi-vType trip input: pass comma-separated `--trip-files` to `duarouter` / `-t` once to
  `duaIterate.py` (not repeated `-t` flags).
- **ADD** runnable workspace layout under a scenario root (`network/`, `demand/`, `assignment/`, `sim/`,
  `sources/`, `build-manifest.json`) aligned with the Karlsruhe reference tree.
- **ADD** build manifest with per-stage content fingerprints; **v1 invalidation:** any `net.xml`
  revision triggers a **full assignment rebuild** (reuse trips when OMX/SQLite unchanged); document
  when demand stages must also rebuild (connector/topology or matrix changes).
- **ADD** optional `sumocfg` emission pointing at `network/net.net.xml` + `assignment/routes.xml` (sim
  execution itself remains out of scope — ADR-015 optional run is not required for v1 done).
- **ADD** CLI module entry (`python -m gis.cli.build_scenario` or equivalent) so operators do not set
  `PYTHONPATH` manually.
- **Out of scope v1:** HTTP API wiring (`POST /v1/scenarios` still uses GeoJSON path), VISUM control
  plans (`import-control-plan`), OMX time-slicing, libsumo dynamic routing, incremental/partial route
  invalidation, simulation run orchestration.

## Capabilities

### New Capabilities

- `demand-assignment`: End-to-end VISUM demand + assignment orchestration; `duaIterate` default;
  workspace layout + manifest; net-change → route rebuild; CLI entry; optional `sumocfg`; Karlsruhe
  acceptance criteria (non-empty `routes.xml`).

### Modified Capabilities

- `scenario-orchestration`: Extend target pipeline to include the VISUM OMX + SQLite demand path and
  name assignment (`duaIterate` preferred over bare `duarouter`) as a first-class orchestration step
  with manifest-driven invalidation.

## Impact

- **Code (writable roots only, ADR-009):** `tools/import/gis/orchestrate/` (assignment module, extend
  `demand.py` options), `tools/import/gis/workspace/` (layout + manifest), new `tools/import/gis/cli/`
  (thin CLI). Invoke upstream `tools/assign/duaIterate.py` and `duarouter` via subprocess only — no
  upstream edits.
- **Tests:** `tests/tools/import/gis/demand/` (assignment wiring, CLI flags), opt-in Karlsruhe smoke
  (routes non-empty, manifest invalidation).
- **Specs:** `specs/interfaces.md` (new cross-module contracts, `unverified` until reconcile);
  `specs/coverage.md` (slice focus update after apply).
- **Reference workspace:** `c:\tmp\karlsruhe\` validated as acceptance fixture (outside repo).
