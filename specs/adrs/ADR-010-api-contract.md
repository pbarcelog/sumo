# ADR-010: API Contract (REST)

**Status:** Draft — **workshop required**
**Tier:** B
**Blocks:** First API implementation OpenSpec change

## Context

PRD §3 defines charter-level journeys. Exact REST resources, upload limits, and error contracts need specification.

## Proposed resources (draft)

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/scenarios` | Create build job (multipart uploads) |
| GET | `/v1/scenarios/{id}` | Scenario metadata |
| GET | `/v1/scenarios/{id}/status` | Build progress |
| GET | `/v1/scenarios/{id}/artifacts` | List/download artifacts |
| POST | `/v1/scenarios/{id}/run` | Start simulation |
| GET | `/v1/scenarios/{id}/runs/{run_id}` | Run status |

## Open questions

- Max upload size per format?
- Layer selection for GPKG (`?layer=roads`)?
- Build options schema (JSON body vs query params)?
- Auth deferred to v2?

## Decision

**Pending workshop.** OpenAPI spec to be authored as part of first implementation change.

## Consequences

- `specs/standards/api-standards.md` activates on Accept.

## References

- PRD §3, §4
