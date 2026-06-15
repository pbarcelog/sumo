<!-- GENERATED FILE — DO NOT EDIT DIRECTLY.
     Source: ai/ directory.  Regenerate: python scripts/sync_ai.py -->

---
name: check-spec
description: >-
  Run sumo-spec-guard audit against an OpenSpec change. Validates proposal, design, tasks, and delta spec against AGENTS.md, PRD, glossary, and post-apply discipline.
---
# Check Spec

Launch `sumo-spec-guard` in **audit mode** against an OpenSpec change.

## Input resolution

- Change name → `openspec/changes/<name>/`
- If no input: `openspec list --json`; use sole active change or ask user.
- Missing artefacts → report and stop.

## Workflow

1. Resolve change folder.
2. Launch sumo-spec-guard with `mode: audit`.
3. Return report verbatim — do not summarise or auto-fix.

Audit mode is advisory only. Gate mode runs inside `/sumo-archive`.
