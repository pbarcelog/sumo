# ADR Registry

**Authoritative index** of architecture decision records. Update this file when an ADR changes state — do not duplicate the table in `AGENTS.md`.

| # | Title | File | Tier | State | Blocker |
|---|---|---|---|---|---|
| ADR-001 | SUMO Module Map | [ADR-001-module-map.md](adrs/ADR-001-module-map.md) | A | **Draft** | — |
| ADR-002 | Network Import Pipeline | [ADR-002-network-import.md](adrs/ADR-002-network-import.md) | A | **Draft** | — |
| ADR-003 | Shape/POI Import (polyconvert) | [ADR-003-shape-import.md](adrs/ADR-003-shape-import.md) | A | **Draft** | — |
| ADR-004 | GDAL Build Dependency | [ADR-004-gdal-dependency.md](adrs/ADR-004-gdal-dependency.md) | A | **Draft** | — |
| ADR-005 | OD / Demand Pipeline | [ADR-005-od-demand.md](adrs/ADR-005-od-demand.md) | A | **Draft** | — |
| ADR-006 | Python Orchestration Pattern | [ADR-006-python-orchestration.md](adrs/ADR-006-python-orchestration.md) | A | **Draft** | — |
| ADR-007 | Data Contracts (XML/XSD) | [ADR-007-data-contracts.md](adrs/ADR-007-data-contracts.md) | A | **Draft** | — |
| ADR-008 | API Stack | [ADR-008-api-stack.md](adrs/ADR-008-api-stack.md) | B | **Draft** | Workshop |
| ADR-009 | Code Placement | [ADR-009-code-placement.md](adrs/ADR-009-code-placement.md) | B | **Accepted** | — |
| ADR-010 | API Contract (REST) | [ADR-010-api-contract.md](adrs/ADR-010-api-contract.md) | B | **Draft** | Workshop |
| ADR-011 | GIS Normalization Layer | [ADR-011-gis-normalization.md](adrs/ADR-011-gis-normalization.md) | B | **Draft** | Workshop |
| ADR-012 | OMX Adapter | [ADR-012-omx-adapter.md](adrs/ADR-012-omx-adapter.md) | B | **Draft** | Workshop |
| ADR-013 | SQLite Role | [ADR-013-sqlite-role.md](adrs/ADR-013-sqlite-role.md) | B | **Draft** | Workshop |
| ADR-014 | TAZ Derivation | [ADR-014-taz-derivation.md](adrs/ADR-014-taz-derivation.md) | B | **Draft** | Workshop |
| ADR-015 | Simulation Execution | [ADR-015-simulation-execution.md](adrs/ADR-015-simulation-execution.md) | B | **Draft** | Workshop |

## Conventions

- File pattern: `specs/adrs/ADR-NNN-<slug>.md`
- States: `Draft → Proposed → Accepted | Superseded`
- Tier **A**: document as-built from codebase; may reach **Accepted (documented from code)** after reconciliation.
- Tier **B**: workshop decisions; gate API implementation. Checklist: [workshop-tier-b.md](workshop-tier-b.md).

## Maintenance

When an ADR file's status changes, update **both** the ADR file header and this registry row in the same change.
