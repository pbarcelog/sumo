<!-- GENERATED FILE — DO NOT EDIT DIRECTLY.
     Source: ai/ directory.  Regenerate: python scripts/sync_ai.py -->

# SUMO GIS API — Claude Code Configuration

See `AGENTS.md` for the full project context, domain glossary, ADR status, and hard rules.
This file contains only Claude Code-specific additions.

---

## Model guidance

High-reasoning tasks (ADR design, slice extraction, cross-slice reconciliation, spec guard audits): use the strongest available model.
Routine tasks (file edits, status checks, commits): any model.

---

## Slash commands

### OpenSpec commands (managed by OpenSpec — do not edit)
- `/opsx:propose` — start a new change
- `/opsx:explore` — explore an idea
- `/opsx:apply` — implement tasks
- `/opsx:archive` — finalize a change

### Custom commands (in `.claude/commands/`)

| Command | Purpose |
| --- | --- |
| `/check-spec <change-name>` | Run sumo-spec-guard audit against an OpenSpec change |
| `/sumo-apply [<change-name>]` | Project-aware OpenSpec task execution |
| `/sumo-archive [<change-name>]` | Project-aware OpenSpec archive |
| `/sumo-propose <change-name>` | Project-aware OpenSpec proposal |

---

## Subagents

Subagent definitions live in `.claude/agents/`. Each file = one persona.
Invoke via the activation phrase from `AGENTS.md`, via a slash command, or via the Agent tool.

| File | Purpose | Activation phrase |
| --- | --- | --- |
| `codebase-analyst.md` | Extracts architecture from a SUMO codebase slice | `Act as Codebase Analyst for <slice>` |
| `reconcile-reviewer.md` | Reviews cross-slice consistency of glossary, interfaces, and ADRs after reconciliation passes (R1, R2) | `Act as Reconcile Reviewer` |
| `sumo-spec-guard.md` | Audits OpenSpec changes against AGENTS.md hard rules, PRD quality bars, glossary, OMX/GDAL gaps, and post-apply discipline | `Act as SUMO Spec Guard for <change-name>` |

---

## Hooks

`SessionStart` runs `ai/scripts/session-start.ps1` (PowerShell 5.1+) on session start and resume.
Output: current branch, ADR inventory with status, uncommitted spec changes, and a reminder of the available agents/commands.
Disable by removing the `hooks` block from `.claude/settings.local.json`.

---

## Key file paths

| File | Purpose |
|---|---|
| `AGENTS.md` | Universal agent instructions, writable allowlist |
| `specs/standards/architecture.md` | **Read before coding** — upstream vs fork, integration style |
| `specs/prd.md` | Product charter (GIS API) |
| `specs/glossary.md` | Domain glossary |
| `specs/interfaces.md` | Cross-module contract registry |
| `specs/coverage.md` | Context extraction schedule, current focus, ledger |
| `specs/adr-registry.md` | ADR status index |
| `specs/adrs/ADR-NNN-*.md` | Architecture Decision Records |
| `specs/workshop-tier-b.md` | Tier B decision checklist |
| `openspec/config.yaml` | OpenSpec artifact rules (not hard product rules) |
| `openspec/changes/` | In-flight changes |
| `openspec/specs/` | Archived capabilities |

### Writable roots (fork-owned)

| Path | Purpose |
|---|---|
| `tools/import/gis/**` | GIS API implementation (ADR-009) |
| `tests/tools/import/gis/**` | Tests for GIS API |

### Read-only reference (upstream SUMO)

| Path | Purpose |
|---|---|
| `tools/osmBuild.py` | Orchestration pattern (ADR-006) |
| `tools/import/gtfs/`, `tools/import/visum/`, … | Existing import pipelines — do not edit |
| `tools/sumolib/` | Python SUMO library — import only |
| `src/netimport/`, `src/polyconvert/`, `src/od/` | C++ import/demand — reference only |
| `data/xsd/` | XML schema contracts |
| `docs/web/docs/` | Upstream SUMO user documentation |

---

## Git conventions

- Commit message format: `type(scope): description`
  - Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`
  - Scope examples: `adr-006`, `prd`, `openspec`, `gis-api`, `specs`
- EPL derivative work: see `src/README_Contributing.md` before modifying `src/` or `tools/`.
- Do not edit generated AI files — edit `ai/` and run `python scripts/sync_ai.py`.
- Do not edit OpenSpec-managed skills under `.claude/skills/openspec-*`.
