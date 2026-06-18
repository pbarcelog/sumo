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
| **Change** | `import-network-sqlite` — VISUM SQLite network import applied under `tools/import/gis/` |
| **Next** | Archive `import-network-sqlite` when PRD §6 e2e passes (OD import + runnable Karlsruhe scenario) |
| **Blockers** | GPKG/pyogrio path unverified in CI; full Karlsruhe microsim blocked on OD import and control-plan work |
| **Last completed** | import-network-sqlite netconvert smoke (eclipse-sumo 1.27.0): Karlsruhe `net.xml` builds and loads; 23/23 tests pass |

*Writable code root: `tools/import/gis/**` (ADR-009).*

---

## ADR index

See [adr-registry.md](adr-registry.md) — not duplicated here.
