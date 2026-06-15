# ADR-008: API Stack

**Status:** Draft — **workshop required**
**Tier:** B
**Blocks:** First API implementation OpenSpec change

## Context

PRD §1 requires an HTTP API. Framework, async job handling, and packaging are undecided.

## Options

| Option | Pros | Cons |
|---|---|---|
| **A: FastAPI + sync subprocess** | Simple; matches osmBuild subprocess model | Long requests block; no native job queue |
| **B: FastAPI + background tasks (asyncio)** | Built-in; light weight | No persistence across restarts |
| **C: FastAPI + Celery/RQ + Redis** | Durable jobs; scalable | Infra complexity |
| **D: Flask + Gunicorn** | Familiar | Less OpenAPI-native than FastAPI |

## Packaging

| Option | Notes |
|---|---|
| Docker single container | SUMO binaries + API + GDAL |
| Bare metal | `SUMO_HOME` on host; API as systemd service |

## Decision

**Pending workshop with Pablo.**

Recommendation for v1 prototype: **Option A or B** (FastAPI) with file-based job status; escalate to C if build times exceed HTTP timeout.

## Consequences

- ADR-010 REST design depends on sync vs async job model.
- ADR-015 simulation execution shares job infrastructure.

## References

- PRD §3
