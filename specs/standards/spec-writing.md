# Spec Writing Standards

## Language

- Specs and ADRs: **English**
- Conversation with Pablo: English or Spanish

## Structure

| Artifact | Template |
|---|---|
| PRD | `specs/prd.md` — numbered sections (§) |
| ADR | `specs/adrs/ADR-NNN-<slug>.md` — Context, Decision, Consequences, Status |
| OpenSpec change | `openspec/changes/<name>/` — proposal, design, tasks, specs/ |

## Rules

1. Every new requirement cites PRD § or states `team decision`.
2. Architecture diagrams: **Mermaid only**.
3. Point to upstream `docs/web/docs/` instead of copying user manuals.
4. Mark `unverified` claims until slice reconciliation.
5. Update `specs/adr-registry.md` and the ADR file when status changes — do not duplicate tables in `AGENTS.md`.
6. Update `specs/interfaces.md` when crossing module boundaries.

## ADR states

`Draft → Proposed → Accepted | Superseded`

Tier A brownfield ADRs may use status **Accepted (documented from code)** after reconciliation.
