# ADR-010: API Contract (REST)

**Status:** Accepted
**Tier:** B
**Date:** 2026-06-16

## Context

PRD §3 defines charter-level journeys. Exact REST resources, upload limits, and error contracts need specification.

## Decision

### Resources (v1)

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/scenarios` | Create build job (multipart uploads + optional JSON `build_options`) |
| GET | `/v1/scenarios/{id}` | Scenario metadata |
| GET | `/v1/scenarios/{id}/status` | Build progress and errors |
| GET | `/v1/scenarios/{id}/artifacts` | List artifacts; `?name=` for single download |
| POST | `/v1/scenarios/{id}/run` | Start simulation (ADR-015) |
| GET | `/v1/scenarios/{id}/runs/{run_id}` | Run status and output artifact list |

### Upload limits

- **Max upload size:** 500 MB per file (multipart).
- Reject with `413` and explicit error body per `specs/standards/api-standards.md`.

### GPKG layer selection

- Query parameter **`?layer=<name>`** on upload or build options for per-file layer override.
- Default layer names for well-known roles documented in API (e.g. `zones` for TAZ polygons — ADR-014).

### Build options

- JSON body field `build_options` on `POST /v1/scenarios` for CRS hints, layer map, and binary flags.
- Advanced netconvert/polyconvert flags MAY be exposed via `build_options` after `sumolib.options.pullOptions` discovery (ADR-006).

### Authentication

- **Deferred to v2.** v1 assumes trusted network or reverse-proxy auth.

### OpenAPI

- Author OpenAPI 3.x spec as part of first implementation change (`gis-api-mvp`).

## Consequences

- `specs/standards/api-standards.md` activated on Accept.
- Error shape, job IDs, and logging conventions in api-standards apply to all routes.

## References

- PRD §3, §4
- ADR-008, ADR-011, ADR-014, ADR-015
