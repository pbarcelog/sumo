# Context Extraction — Coverage

**Status:** Complete (R2 Accepted, 2026-06-15)

Historical schedule and ledger: [archive/context-extraction.md](archive/context-extraction.md).  
Reconciliation summary: [reconciliation-r2.md](reconciliation-r2.md).

---

## Current focus

| Field | Value |
|---|---|
| **Mode** | Implementation (in progress) |
| **Branch** | `feature/importPoC` |
| **Change** | `demand-assignment` — VISUM demand + route assignment productized (`build_runnable_scenario`, CLI, manifest invalidation) |
| **Next** | Karlsruhe vClass-correct `assignment/routes.xml`; archive `demand-assignment`; then `import-network-geojson` or `gis-api-mvp` archive |
| **Blockers** | Karlsruhe full `duarouter` run ~1 h; `duaIterate` at full scale unbenchmarked |
| **Last completed** | `import-od-demand` archived (2026-06-22); Karlsruhe microsim smoke to t=300 with manual `routes.xml` + `vtypes.add.xml` |

**Future ideas (not current focus):** [`specs/future/`](future/README.md) — icebox backlog (e.g. PuT demand scenarios 3–4).

*Writable code root: `tools/import/gis/**` (ADR-009).*

---

## ADR index

See [adr-registry.md](adr-registry.md) — not duplicated here.
