---
name: sumo-archive
description: >-
  Project-aware OpenSpec archive. Runs sumo-spec-guard in gate mode before
  /opsx:archive. Updates specs/adr-registry.md and specs/coverage.md when
  applicable.
argument: "[<change-name>]"
invokes_agent: sumo-spec-guard
---

# SUMO Archive

Wrapper around `openspec-archive-change` with strict pre-archive gate.

## Step 1 — Gate via sumo-spec-guard

Invoke `sumo-spec-guard` in **gate** mode. If Blockers exist, **do not archive**.

## Step 2 — Invoke openspec-archive-change

Only after gate passes.

## Step 3 — Post-archive

- Verify `specs/coverage.md` and `specs/adr-registry.md` updated when slice or ADR tasks included.
- Remind: do not add status tables back to `AGENTS.md`.
