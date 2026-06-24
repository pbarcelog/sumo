# Future ideas (icebox)

**Status:** Informal — not committed work  
**Audience:** Product, modellers, implementers

This folder holds **secondary backlog** items: plausible directions, scenario variants, and
research notes that are **not** yet OpenSpec changes and **not** current focus.

## How this relates to other docs

| Location | Purpose |
|---|---|
| [`specs/coverage.md`](../coverage.md) | **Current focus** — what we are doing now |
| [`openspec/changes/`](../openspec/changes/) | **Committed changes** — proposal, design, tasks, delta specs |
| [`specs/adrs/`](../adrs/) | **Accepted architecture** — decisions that govern implementation |
| [`specs/assumptions/`](../assumptions/) | **Provisional business rules** — reviewable, may become ADR or code |
| **`specs/future/` (here)** | **Ideas parking lot** — may promote to OpenSpec or be dropped |

## Rules

1. **No task checkboxes** — ideas only; when work starts, open an OpenSpec change.
2. **English**, Mermaid when diagrams help.
3. Each file should state **status** (`idea`, `candidate`, `promoted`, `dropped`) at the top.
4. Link to PRD §, ADRs, and upstream `docs/web/docs/` where relevant — do not duplicate SUMO manuals.
5. **Do not** place fork product notes under `docs/` — that tree is upstream SUMO documentation (read-only for this project).

## Promotion path

```
idea in specs/future/ → modeller/product sign-off → /opsx:propose <change> → implementation
```

When an idea is promoted, add a one-line “Promoted to `openspec/changes/<name>`” note in the source file and leave the historical rationale in place.

## Ideas index

| File | Topic | Status |
|---|---|---|
| [`demand-pt-scenarios.md`](demand-pt-scenarios.md) | PrT OMX vs GTFS / PuT icebox scenarios | `candidate` |
| [`demand-taz-routing-alternatives.md`](demand-taz-routing-alternatives.md) | SUMO routing options we do not use in v1 (fromTaz routing, `--ignore-errors`, repair, in-sim TAZ) | `idea` |
