# ADR-008: API Stack

**Status:** Accepted
**Tier:** B
**Date:** 2026-06-16

## Context

PRD §1 requires an HTTP API. Framework, async job handling, and packaging are undecided.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A: FastAPI + sync subprocess** | Simple; matches osmBuild subprocess model | Long requests block; no native job queue |
| **B: FastAPI + background tasks (asyncio)** | Built-in; light weight | No persistence across restarts |
| **C: FastAPI + Celery/RQ + Redis** | Durable jobs; scalable | Infra complexity |
| **D: Flask + Gunicorn** | Familiar | Less OpenAPI-native than FastAPI |

## Decision

**Framework:** FastAPI (OpenAPI 3.x native).

**Job model:** FastAPI **asyncio background tasks** for build and simulation steps. Job status persisted as JSON on local filesystem under the scenario workspace (ADR-015). Escalate to Celery/RQ + Redis only if build times exceed acceptable polling windows or multi-instance deployment requires durable queues.

**Packaging:** **Docker** single container — SUMO binaries, GDAL, Python API dependencies, and writable scenario workspace volume.

## Consequences

- ADR-010 REST design uses async job pattern: `POST` returns scenario id immediately; clients poll `GET /v1/scenarios/{id}/status`.
- ADR-015 simulation runs share the same background-task and status-file infrastructure.
- `tools/import/gis/api/` hosts FastAPI app; Uvicorn as ASGI server in container.
- v1 does not require Redis or Celery.

## References

- PRD §3
- ADR-009, ADR-010, ADR-015
