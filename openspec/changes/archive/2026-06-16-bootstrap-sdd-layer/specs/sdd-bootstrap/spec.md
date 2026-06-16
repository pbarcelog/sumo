# SDD Bootstrap

Capability spec: repository infrastructure for spec-driven development on SUMO GIS API fork.

**ADR:** meta
**PRD:** §6

## ADDED Requirements

### Requirement: Universal agent entry point

The repository MUST contain `AGENTS.md` as the universal instruction file for all AI assistants.

#### Scenario: Agent session start

- **WHEN** an agent begins work on this repository
- **THEN** it can read AGENTS.md for layout, hard rules, and OpenSpec workflow

### Requirement: Spec corpus

The repository MUST contain `specs/prd.md`, `specs/glossary.md`, `specs/interfaces.md`, `specs/coverage.md`, `specs/adr-registry.md`, and `specs/adrs/` with ADR-001 through ADR-015.

#### Scenario: Slice documentation

- **WHEN** a codebase analyst completes a slice pass
- **THEN** coverage.md and relevant ADRs are updatable without creating new folder structure

### Requirement: OpenSpec configuration

`openspec/config.yaml` MUST define project context (GIS API, MVP formats, brownfield rules) and artifact rules.

#### Scenario: New OpenSpec change

- **WHEN** `/opsx:propose` runs
- **THEN** OpenSpec injects SUMO GIS API context from config.yaml

### Requirement: AI-agnostic sync

Canonical AI assets MUST live in `ai/` and generate platform files via `scripts/sync_ai.py`.

#### Scenario: Agent definition update

- **WHEN** an agent edits `ai/agents/sumo-spec-guard.md`
- **THEN** running `python scripts/sync_ai.py` updates `.claude/agents/` without hand-editing generated files

### Requirement: Tier B workshop gate

Tier B ADRs (008–015) MUST be Accepted per `specs/workshop-tier-b.md` before the first API implementation OpenSpec apply.

#### Scenario: API implementation allowed

- **WHEN** `gis-api-mvp` apply begins
- **THEN** Tier B ADRs 008–015 are Accepted in `specs/adr-registry.md`
