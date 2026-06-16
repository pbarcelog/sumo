# Context Extraction — Archived Schedule & Ledger

**Archived:** 2026-06-15 (R2 Accepted)  
**Reconciliation:** [reconciliation-r2.md](../reconciliation-r2.md)

---

## Extraction schedule (historical)

| Step | Primary paths | Target ADRs |
|---|---|---|
| 0 | meta | AGENTS, PRD charter, skeleton |
| 1 | `tools/osmBuild.py`, `tools/osmWebWizard.py` | ADR-006 |
| 2 | `src/netimport/`, `src/netbuild/` | ADR-002, ADR-004 |
| 3 | `src/polyconvert/` | ADR-003 |
| 4 | `data/xsd/`, `data/typemap/` | ADR-007 |
| 5 | `src/od/`, od2trips docs | ADR-005 |
| R1 | reconcile | glossary, interfaces, ADR-012 stub |
| 6 | `tools/sumolib/`, traci | ADR-006 extension |
| 7 | `tests/`, `.github/workflows/` | test conventions |
| R2 | reconcile | Tier A → Accepted; Tier B workshop pack |

**Deferred** (unless API needs early): `src/microsim/`, `src/netedit/`, `src/gui/`.

---

## Coverage ledger (final)

| Slice | Primary paths | ADRs | Status | Open questions (caveats) |
|---|---|---|---|---|
| 0 Bootstrap | AGENTS, specs/, openspec/ | — | **Accepted** | — |
| 1 Orchestration | `tools/osmBuild.py`, `osmWebWizard.py` | ADR-006 | **Accepted** | Demand steps not in osmBuild |
| 2 Network import | `src/netimport/`, `src/netbuild/` | ADR-002, ADR-004 | **Accepted** | GeoJSON network gap |
| 3 Shape import | `src/polyconvert/` | ADR-003 | **Accepted** | GPKG unverified |
| 4 Data contracts | `data/xsd/`, `data/typemap/` | ADR-007 | **Accepted** | — |
| 5 OD / demand | `src/od/`, od2trips | ADR-005 | **Accepted** | OMX gap → ADR-012 |
| R1 Reconcile | glossary, interfaces | ADR-012 stub | **Accepted** | [reconciliation-r1.md](../reconciliation-r1.md) |
| 6 sumolib + TraCI | `tools/sumolib/`, `tools/traci/` | ADR-006 ext | **Accepted** | Libsumo/libtraci → ADR-015 |
| 7 Tests / CI | `tests/`, `.github/workflows/` | — | **Accepted** | HTTP harness TBD; see test-strategy |
| R2 Reconcile | Tier A → Accepted | ADR-001–007 | **Accepted** | Tier B workshop |
