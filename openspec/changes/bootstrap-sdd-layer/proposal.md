# Change: bootstrap-sdd-layer

**Status:** Proposed
**Phase:** 0 — SDD infrastructure bootstrap

## Why

Establish spec-driven development infrastructure on the SUMO brownfield fork before GIS API implementation. Agents need AGENTS.md, specs/, openspec/, and ai/ sync pipeline.

## What Changes

- **ADD** `AGENTS.md`, `CLAUDE.md` (generated), `specs/` skeleton, `openspec/config.yaml`
- **ADD** PRD charter, glossary, interfaces, coverage, ADRs 001–015, standards
- **ADD** `ai/` canonical layer + `scripts/sync_ai.py`
- **ADD** Tier B workshop checklist (`specs/workshop-tier-b.md`)
- **NO** SUMO C++ or API implementation code

## Capabilities

### New Capabilities

- `sdd-bootstrap`: Repository has universal agent entry point, spec corpus, and OpenSpec configuration for GIS API fork.

### Modified Capabilities

_None._

## Impact

- All subsequent OpenSpec changes depend on this foundation.
- Tier B ADRs remain Draft until workshop (`specs/workshop-tier-b.md`).

## References

- SUMO SDD Bootstrap Plan
