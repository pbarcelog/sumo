# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

Fork integration tests for the GIS API (IF-TEST-001).

## Layout

| Path | Purpose |
|---|---|
| `test_health.py` | FastAPI health + `checkBinary` smoke |
| `test_omx_adapter.py` | OMX → tazRelation unit tests |
| `health/` | TextTest stub (optional CI) |

Run: `pytest tests/tools/import/gis/`

Requires: `pip install -r tools/import/gis/requirements.txt`
