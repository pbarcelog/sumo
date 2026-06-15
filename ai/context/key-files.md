| File | Purpose |
|---|---|
| `AGENTS.md` | Universal agent instructions, writable allowlist |
| `specs/standards/architecture.md` | **Read before coding** — upstream vs fork, integration style |
| `specs/prd.md` | Product charter (GIS API) |
| `specs/glossary.md` | Domain glossary |
| `specs/interfaces.md` | Cross-module contract registry |
| `specs/coverage.md` | Context extraction schedule, current focus, ledger |
| `specs/adr-registry.md` | ADR status index |
| `specs/adrs/ADR-NNN-*.md` | Architecture Decision Records |
| `specs/workshop-tier-b.md` | Tier B decision checklist |
| `openspec/config.yaml` | OpenSpec artifact rules (not hard product rules) |
| `openspec/changes/` | In-flight changes |
| `openspec/specs/` | Archived capabilities |

### Writable roots (fork-owned)

| Path | Purpose |
|---|---|
| `tools/import/gis/**` | GIS API implementation (ADR-009) |
| `tests/tools/import/gis/**` | Tests for GIS API |

### Read-only reference (upstream SUMO)

| Path | Purpose |
|---|---|
| `tools/osmBuild.py` | Orchestration pattern (ADR-006) |
| `tools/import/gtfs/`, `tools/import/visum/`, … | Existing import pipelines — do not edit |
| `tools/sumolib/` | Python SUMO library — import only |
| `src/netimport/`, `src/polyconvert/`, `src/od/` | C++ import/demand — reference only |
| `data/xsd/` | XML schema contracts |
| `docs/web/docs/` | Upstream SUMO user documentation |
