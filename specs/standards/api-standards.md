# API Standards — SUMO GIS API

**Status:** Accepted (activated 2026-06-16 — ADR-010)
**ADR:** ADR-008, ADR-010, ADR-015

## Conventions

| Topic | Convention |
|---|---|
| API style | REST, OpenAPI 3.x document served at `/v1/openapi.json` |
| Versioning | `/v1/` prefix on all routes |
| Error shape | `{ "error": { "code": string, "message": string, "details": object \| null } }` |
| HTTP codes | `400` validation; `413` upload too large; `404` unknown scenario/run; `409` invalid state transition; `500` internal |
| Job IDs | UUID v4 for scenario id and run id |
| Uploads | `multipart/form-data`; max **500 MB** per file (ADR-010) |
| GPKG layers | `?layer=<name>` query parameter; default role layers documented in OpenAPI |
| Job status | Poll `GET /v1/scenarios/{id}/status`; JSON includes `state`, `step`, `progress`, `error` |
| Logging | Structured JSON logs; fields: `scenario_id`, `run_id`, `step`, `binary`, `exit_code` |
| Workspace | `{workspace}/scenarios/{scenario_id}/` on local filesystem (ADR-015) |

## Build options (JSON)

| Field | Purpose |
|---|---|
| `crs` | Optional EPSG override (ADR-011) |
| `layers` | Map role → layer name (e.g. `zones`, `roads`) |
| `sqlite_joins` | Attribute table joins (ADR-013) |
| `vType` | Default vehicle type for OMX relations (ADR-012) |

## Deferred (v1)

- Authentication / API keys (ADR-010)
- Rate limiting
- WebSocket progress streaming (polling via status endpoint)
- S3-compatible artifact storage (ADR-015)
- TraCI / libsumo simulation control (ADR-015)

## References

- ADR-008 (FastAPI, background tasks, Docker)
- ADR-010 (REST resources)
- ADR-015 (subprocess sumo, filesystem artifacts)
