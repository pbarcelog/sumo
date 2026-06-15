---
name: sumo-propose
description: >-
  Project-aware OpenSpec proposal. Pre-loads AGENTS.md, PRD, glossary, and
  openspec/config.yaml, invokes openspec-propose skill, then audits via
  sumo-spec-guard. Prefer over bare /opsx:propose for SUMO changes.
argument: "<change-name>"
invokes_agent: sumo-spec-guard
---

# SUMO Propose

Project-aware wrapper around `openspec-propose`. Adds SUMO pre-flight and post-creation audit.

**Prefer `/sumo-propose` over `/opsx:propose`** for this fork.

## Step 1 — Pre-flight

Read: `AGENTS.md`, `specs/standards/architecture.md`, `specs/prd.md`, `specs/glossary.md`, `openspec/config.yaml`.

Announce: *Pre-flight loaded: AGENTS.md, architecture, PRD, glossary, openspec/config.yaml.*

## Step 2 — Invoke openspec-propose

Apply constraints:

- Cite PRD § or `team decision` on requirements.
- Respect PRD §4 quality bars.
- OMX → ADR-012; no native OMX in SUMO.
- Mermaid diagrams only.
- Prefer Python orchestration (ADR-006) over C++ core edits.

## Step 3 — Post-check via sumo-spec-guard (audit mode)

Return audit report verbatim.

## Step 4 — Verdict

| Verdict | Action |
|---------|--------|
| Approve | Ready for `/sumo-apply` |
| Approve-with-changes | Surface findings; user edits artefacts |
| Block | Do not apply; fix Blockers first |
