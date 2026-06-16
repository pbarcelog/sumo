# Change: document-sumolib-traci-slice

**Status:** Proposed
**Slice:** 6 — `tools/sumolib/`, `tools/traci/` → extend ADR-006
**Normative output:** ADR-006 (sumolib + TraCI sections), `specs/interfaces.md`, glossary

## Why

Slice 1 documented orchestration from `osmBuild.py` but only summarized sumolib. The GIS API orchestrator will import sumolib for binary resolution, config/XML helpers, and net inspection; simulation execution (ADR-015) depends on understanding TraCI vs subprocess vs libsumo paths.

## What Changes

- **DOCUMENT** sumolib API surface for orchestrators in ADR-006 (binary, options, net, xml, files, shapes, geomhelper scope).
- **DOCUMENT** TraCI connection lifecycle, domain subset, error model, and Libsumo/libtraci switch in ADR-006.
- **ADD** interface rows for sumolib helpers and TraCI connection in `specs/interfaces.md`.
- **ADD** glossary terms: Libsumo, Libtraci, checkBinary, `.sumocfg`.
- **UPDATE** `specs/coverage.md` slice 6 → Draft; Current focus → slice 7.
- **NO CODE** changes under `src/` or existing `tools/`.

## Capabilities

### New Capabilities

- `sumolib-traci-integration`: Requirements and contracts for sumolib orchestration helpers and simulation control plane options (ADR-015 dependency).

### Modified Capabilities

- `scenario-orchestration`: Extended by sumolib detail and post-build simulation sequences.

## Impact

- **Specs:** ADR-006, interfaces.md, glossary.md, coverage.md.
- **Downstream:** ADR-015 workshop, slice 7 test survey.
- **Tests:** None in this documentation change.

## References

- ADR-006, ADR-015
- `docs/web/docs/Tools/Sumolib.md`, `docs/web/docs/TraCI/index.md`, `docs/web/docs/Libsumo.md`
