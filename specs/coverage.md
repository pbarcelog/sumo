# Context Extraction — Coverage

**Status:** Complete (R2 Accepted, 2026-06-15)

Historical schedule and ledger: [archive/context-extraction.md](archive/context-extraction.md).  
Reconciliation summary: [reconciliation-r2.md](reconciliation-r2.md).

---

## Current focus

| Field | Value |
|---|---|
| **Mode** | Idle — pick next epic |
| **Branch** | `feature/importPoC` |
| **Change** | — |
| **Next** | Wire GeoJSON demand into `build_runnable_scenario()` or propose next slice (e.g. control plans) |
| **Blockers** | — |
| **Last completed** | `import-od-demand-geojson` archived (2026-06-26) → `openspec/specs/od-import-demand-geojson/spec.md` |

**Pending (non-blocking):** full-day Karlsruhe `duarouter`, full-scale `duaIterate`, and `sumo-gui`
acceptance on the large reference model — revisit when a smaller network fixture exists.

**Future ideas (not current focus):** [`specs/future/`](future/README.md) — icebox backlog (e.g. PuT demand scenarios 3–4).

*Writable code root: `tools/import/gis/**` (ADR-009).*

---

## ADR index

See [adr-registry.md](adr-registry.md) — not duplicated here.
