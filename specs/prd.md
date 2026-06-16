# Product Requirements Document — SUMO GIS API (Charter)

**Status:** Draft (charter)
**Version:** 0.1

---

## §1 Vision

Build an **HTTP API** that accepts universal spatial information files and an OMX origin–destination matrix, orchestrates existing SUMO tooling, and produces **runnable simulation scenarios** (network, shapes, demand, routes, optional simulation run).

The API **does not modify** upstream SUMO (`src/` or existing `tools/` files). New code lives under **`tools/import/gis/`** (ADR-009). It **wraps and normalizes** inputs in that package, then invokes SUMO binaries via `sumolib`.

---

## §2 MVP scope

### In scope (v1)

| Input | Role |
|---|---|
| **GeoJSON** | Spatial layers → network lines (via preprocessing) and/or TAZ polygons and shapes via polyconvert |
| **GeoPackage (.gpkg)** | Multi-layer spatial container; layer selection and CRS normalization in API |
| **SQLite** | Spatial and/or attribute data (semantics per ADR-013 — SpatiaLite vs plain tables) |
| **OMX** | Origin–destination matrix for demand generation (adapter per ADR-012) |

| Capability | Description |
|---|---|
| Scenario build | Orchestrate netconvert, polyconvert, od2trips, duarouter as needed |
| Artifact delivery | Expose `.net.xml`, trips, routes, logs, optional additional files |
| Optional run | Trigger `sumo` simulation from API (ADR-015) |

### Out of scope (v1)

- Modifications to any existing file under `src/` or `tools/` (read-only upstream)
- Shapefile-first pipeline as MVP (supported upstream but not primary API path)
- Native C++ importers for GPKG or OMX inside SUMO core
- Replacing netconvert/polyconvert internals
- Full OSM Web Wizard parity (reference only — see `tools/osmWebWizard.py`)
- Authentication and multi-tenancy (deferred — ADR-010)

### Open items

*All Tier B workshop items resolved 2026-06-16 — see ADR-008 through ADR-015.*

---

## §3 User journeys (API-level)

Exact REST shape is **ADR-010**. Charter-level journeys:

1. **`POST /scenarios`** — Upload or reference spatial files + OMX + build options → returns job/scenario id.
2. **`GET /scenarios/{id}/status`** — Build progress and error detail.
3. **`GET /scenarios/{id}/artifacts`** — Download network, demand, routes, logs.
4. **`POST /scenarios/{id}/run`** — Optional simulation execution; returns run status and outputs.

---

## §4 Quality bars

| Bar | Requirement |
|---|---|
| Determinism | Same inputs + options → reproducible artifacts (modulo SUMO version) |
| Fail loud | GDAL, CRS, schema, or OMX conversion failures return explicit errors — no silent drops |
| CRS | Documented and testable projection handling; log transforms applied |
| Schema | No silent attribute loss; warn or fail on unmapped required fields |
| Traceability | Build logs retained with scenario artifacts |

---

## §5 References to existing SUMO capabilities

Do not duplicate — cite upstream:

| Topic | Reference |
|---|---|
| Network GIS import | [docs/web/docs/Networks/Import/](docs/web/docs/Networks/Import/) |
| Shape/POI import | [docs/web/docs/polyconvert.md](docs/web/docs/polyconvert.md) |
| OD matrices | [docs/web/docs/Demand/Importing_O/D_Matrices.md](docs/web/docs/Demand/Importing_O/D_Matrices.md) |
| Orchestration reference | [tools/osmBuild.py](tools/osmBuild.py) |
| Module map | [docs/web/docs/Developer/Implementation_Notes/Sumo_Modules.md](docs/web/docs/Developer/Implementation_Notes/Sumo_Modules.md) |
| Python style | [docs/web/docs/Developer/PythonFileTemplate.md](docs/web/docs/Developer/PythonFileTemplate.md) |

---

## §6 Success criteria (charter)

- [ ] Tier A ADRs Accepted (documented from code)
- [ ] Tier B ADRs Accepted (workshop decisions)
- [ ] OpenSpec change for API MVP proposed and archived
- [ ] End-to-end: GPKG or GeoJSON + OMX → runnable scenario via API

---

## §7 ADR index

See [specs/adr-registry.md](adr-registry.md) and `specs/adrs/`.
