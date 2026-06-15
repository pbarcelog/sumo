# Context Extraction — Coverage & Schedule

Tracks **brownfield documentation passes** (slice extraction). Update after each slice and reconciliation.

For ADR index and status, see [adr-registry.md](adr-registry.md) — not duplicated here.

---

## Current focus

| Field | Value |
|---|---|
| **Mode** | context extraction |
| **Next slice** | **6** — `tools/sumolib/`, TraCI → extend ADR-006 |
| **Blockers** | Tier B workshop ([workshop-tier-b.md](workshop-tier-b.md)) before API implementation |
| **Last completed** | Slices 0–5 + R1 reconcile (Draft ADRs) |

*Update this section when a slice or reconciliation completes.*

---

## Extraction schedule

Ordered passes. Each slice produces glossary entries, ADR updates, interface stubs, and a ledger row below.

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

## Coverage ledger

| Slice | Primary paths | ADRs | Status | Open questions |
|---|---|---|---|---|
| 0 Bootstrap | AGENTS, specs/, openspec/ | — | **Accepted** | — |
| 1 Orchestration | `tools/osmBuild.py`, `osmWebWizard.py` | ADR-006 | **Draft** | Demand steps not in osmBuild |
| 2 Network import | `src/netimport/`, `src/netbuild/` | ADR-002, ADR-004 | **Draft** | GeoJSON network gap |
| 3 Shape import | `src/polyconvert/` | ADR-003 | **Draft** | GPKG unverified |
| 4 Data contracts | `data/xsd/`, `data/typemap/` | ADR-007 | **Draft** | — |
| 5 OD / demand | `src/od/`, od2trips | ADR-005 | **Draft** | OMX gap → ADR-012 |
| R1 Reconcile | glossary, interfaces | ADR-012 stub | **Draft** | See [reconciliation-r1.md](reconciliation-r1.md) |
| 6 sumolib | `tools/sumolib/` | ADR-006 ext | **Pending** | — |
| 7 Tests / CI | `tests/`, `.github/` | — | **Pending** | — |
| R2 Reconcile | Tier A → Accepted | ADR-001–007 | **Pending** | Tier B workshop |

**Status values:** Pending → Draft → Accepted

---

## Historical note

When context extraction is complete (R2 Accepted), move the schedule/ledger to `specs/archive/context-extraction.md` and leave only a one-line pointer here if needed.
