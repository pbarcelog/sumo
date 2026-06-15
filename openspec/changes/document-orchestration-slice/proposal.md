# Change: document-orchestration-slice

**Status:** Proposed
**Slice:** 1 — Python orchestration (`tools/osmBuild.py`)
**Normative output:** ADR-006, `specs/interfaces.md` orchestration sections

## Why

The GIS API orchestrates SUMO binaries rather than reimplementing C++ import logic. Before building the HTTP service, we must document the as-built orchestration pattern from `osmBuild.py` and define the target multi-step pipeline (network + shapes + demand) in specs.

`osmBuild.py` is OSM-specific and covers only netconvert + polyconvert. The API MVP requires extending this pattern with OMX adapter, od2trips, and duarouter (ADR-005, ADR-012).

## What Changes

- **DOCUMENT** ADR-006 from code analysis of `tools/osmBuild.py` and `tools/osmWebWizard.py`.
- **DOCUMENT** orchestration interfaces in `specs/interfaces.md` (reference + target sequences).
- **ADD** OpenSpec capability `scenario-orchestration` describing orchestration requirements for the GIS API.
- **UPDATE** `specs/coverage.md` slice 1 status.
- **NO CODE** changes to SUMO binaries in this change — documentation only.

## Capabilities

### New Capabilities

- `scenario-orchestration`: Requirements for Python orchestration of SUMO binaries — osmBuild pattern, config file generation, subprocess discipline, and target API pipeline including demand steps.

### Modified Capabilities

_None._

## Impact

- **Specs:** ADR-006, interfaces.md, coverage.md, glossary (orchestrator term).
- **Downstream:** ADR-008–015 implementation changes depend on this capability.
- **Tests:** None in this documentation change.

## References

- PRD §1, §5
- ADR-006
