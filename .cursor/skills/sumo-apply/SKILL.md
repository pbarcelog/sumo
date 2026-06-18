<!-- GENERATED FILE — DO NOT EDIT DIRECTLY.
     Source: ai/ directory.  Regenerate: python scripts/sync_ai.py -->

---
name: sumo-apply
description: >-
  Project-aware OpenSpec task execution. Pre-loads AGENTS.md and relevant ADRs, invokes openspec-apply-change skill with SUMO constraints (orchestration, EPL, spec-first fixes).
---
# SUMO Apply

Wrapper around `openspec-apply-change` with SUMO context.

## Pre-flight

Read `AGENTS.md`, change proposal/design/tasks, relevant ADRs for the change scope.

## During apply

- Follow `specs/standards/python-standards.md` for new Python code.
- Use `sumolib.checkBinary` for SUMO subprocess calls (ADR-006).
- Post-apply fixes: update artefacts before code (AGENTS.md hard rule #5).

## Post-apply (optional)

Suggest `/check-spec <name>` before archive.
