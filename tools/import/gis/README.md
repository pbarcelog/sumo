# SUMO GIS API (fork-owned)

HTTP service and orchestration for GeoJSON, GeoPackage, SQLite, and OMX inputs.

**Writable fork module** — see ADR-009. Do not modify sibling packages under `tools/import/`.

## Layout

| Path | Role |
|---|---|
| `api/` | FastAPI application (ADR-008, ADR-010) |
| `normalize/` | GIS preprocessing (ADR-011, ADR-013): GeoJSON/GPKG pipeline; VISUM SQLite (`visum_sqlite.py`, `modes.py`, `speed.py`) |
| `omx/` | OMX → tazRelation adapter (ADR-012) |
| `orchestrate/` | SUMO binary pipeline (ADR-006): scenario `pipeline.py`; SQLite `netbuild.py` (plain XML + netconvert) |
| `workspace/` | Scenario filesystem and job status (ADR-015) |

## Run locally

```bash
export SUMO_HOME=/path/to/sumo
export GIS_API_WORKSPACE=/tmp/gis-scenarios
pip install -r tools/import/gis/requirements.txt
python tools/import/gis/api/main.py
```

OpenAPI: `http://localhost:8000/v1/openapi.json`

## Tests

```bash
pip install eclipse-sumo   # netconvert/sumo on PATH for build smoke tests
pytest tests/tools/import/gis/
```
