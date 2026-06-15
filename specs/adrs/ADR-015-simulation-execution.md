# ADR-015: Simulation Execution

**Status:** Draft — **workshop required**
**Tier:** B

## Context

PRD §3 journey 4: optional simulation run from API.

## Options

| Option | Approach |
|---|---|
| **A** | `subprocess` `sumo -c scenario.sumocfg` | Simple; matches osmBuild |
| **B** | TraCI remote control | Programmatic; complex |
| **C** | sumo-gui for debug only | Not for API production |
| **D** | libsumo / libtraci embedded | In-process; advanced |

## Artifact storage

| Option | Notes |
|---|---|
| File system per scenario id | `scenarios/{id}/artifacts/` |
| Object storage (S3-compatible) | Production deployment |

## Decision

**Pending workshop.**

Recommendation v1: **Option A** + file-system artifacts; TraCI deferred.

## Consequences

- Shares job model with ADR-008.
- Output: tripinfo, summary xml per SUMO defaults.

## References

- PRD §3
- ADR-006 subprocess pattern
