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

### Fork implementation (`tools/import/gis/`)

Operational detail also in `specs/interfaces.md` reconciliation log and `specs/coverage.md` § Current focus.

| Module | Role | Status |
|---|---|---|
| `api/` | FastAPI HTTP service (ADR-008, ADR-010) | partial |
| `normalize/pipeline.py`, `crs.py`, `models.py` | GeoJSON/GPKG normalization (ADR-011) | partial |
| `normalize/visum_sqlite.py`, `modes.py`, `speed.py` | VISUM SQLite network import | implemented (`import-network-sqlite`) |
| `orchestrate/pipeline.py`, `subprocess_run.py` | Scenario build orchestration (ADR-006) | partial |
| `orchestrate/netbuild.py` | Plain XML + `netconvert` for SQLite network | implemented |
| `omx/adapter.py`, `validate.py` | OMX → tazRelation (ADR-012) | partial |
| `workspace/` | Scenario dirs and job status (ADR-015) | partial |

**Dev SUMO binaries:** `pip install eclipse-sumo` puts `netconvert`/`sumo` on `PATH` for tests and smoke runs without compiling `src/`. `sumolib` still comes from this repo (`tools/sumolib/`).

**OpenSpec changes (in-flight folder):** `gis-api-mvp` and `import-network-sqlite` applied; `import-network-geojson` spec-only; next epic slices: OD import (`import-od-demand`), control plans (`import-control-plan`).

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
