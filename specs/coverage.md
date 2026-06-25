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
| **Change** | Choose next: `gis-api-mvp` archive or `import-network-geojson` (spec-only) |
| **Next** | Archive `gis-api-mvp` or propose/apply `import-network-geojson` |
| **Blockers** | — |
| **Last completed** | `demand-assignment` archived (2026-06-25) — VISUM demand + assignment (`build_runnable_scenario`, CLI, manifest, `duaIterate` default) |

**Pending (non-blocking):** full-day Karlsruhe `duarouter`, full-scale `duaIterate`, and `sumo-gui`
acceptance on the large reference model — revisit when a smaller network fixture exists.

**Future ideas (not current focus):** [`specs/future/`](future/README.md) — icebox backlog (e.g. PuT demand scenarios 3–4).

*Writable code root: `tools/import/gis/**` (ADR-009).*

---

## ADR index

See [adr-registry.md](adr-registry.md) — not duplicated here.
