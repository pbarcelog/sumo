# API Standards — SUMO GIS API

**Status:** Draft — activate after ADR-010 Accepted.

## Planned conventions

| Topic | Convention |
|---|---|
| API style | REST, OpenAPI 3.x document |
| Error shape | `{ "error": { "code", "message", "details" } }` |
| Job IDs | UUID v4 for scenario/build jobs |
| Uploads | Multipart for files; optional URL reference for large assets |
| Logging | Structured JSON logs; include `scenario_id`, `step`, `binary`, `exit_code` |
| Versioning | `/v1/` prefix on all routes |

## Deferred (v1)

- Authentication / API keys
- Rate limiting
- WebSocket progress streaming (polling via status endpoint for v1)

See ADR-010 for REST resource design.
