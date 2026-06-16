# ADR-015: Simulation Execution

**Status:** Accepted
**Tier:** B
**Date:** 2026-06-16

## Context

PRD §3 journey 4: optional simulation run from API.

## Options considered

| Option | Approach |
|---|---|
| **A** | `subprocess` `sumo -c scenario.sumocfg` | Simple; matches osmBuild |
| **B** | TraCI remote control | Programmatic; complex |
| **C** | sumo-gui for debug only | Not for API production |
| **D** | libsumo / libtraci embedded | In-process; advanced |

## Decision

**Execution (v1): Option A** — `subprocess` invocation of `sumo` via `sumolib.checkBinary`, with `.sumocfg` generated under the scenario workspace (osmWebWizard pattern — ADR-006).

- TraCI socket, libsumo, and libtraci (**Option D**) deferred to v2 unless a concrete v1 requirement emerges.
- Outputs: `tripinfos.xml`, `summary.xml`, and other paths declared in `.sumocfg` / `build_options`.

**Artifact storage:** **Local filesystem** per scenario id:

```
{workspace}/scenarios/{scenario_id}/
  build/          # net, poly, demand artifacts
  runs/{run_id}/  # simulation outputs
  status.json     # build/run job state (ADR-008)
```

Object storage (S3-compatible) deferred; path abstraction MAY be introduced without changing v1 default.

## Consequences

- Shares asyncio background job model with ADR-008.
- `POST /v1/scenarios/{id}/run` enqueues subprocess; `GET .../runs/{run_id}` polls completion.
- Integration tests use `SUMO_BINARY` / `checkBinary` pattern (`specs/test-strategy.md`).

## References

- PRD §3
- ADR-006, ADR-008, ADR-010
