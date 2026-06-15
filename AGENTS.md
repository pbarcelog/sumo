# SUMO GIS API — Agent Instructions

Universal entry point for any AI coding assistant (Claude Code, Cursor, Codex, API agents).
Canonical AI assets live in `ai/`. Platform-specific files are generated — see the AI configuration layer section below.
Claude Code users: see also `CLAUDE.md` for Claude-specific configuration.
Cursor users: see also `.cursor/rules/sumo-cursor.mdc` for Cursor-specific configuration.

---

## Project snapshot

| Field | Value |
|---|---|
| Product | **SUMO GIS API** — HTTP service on top of Eclipse SUMO |
| Base | Brownfield Eclipse SUMO (traffic simulation) |
| Goal | Ingest GeoJSON, GeoPackage, SQLite + OMX OD matrices; build and run SUMO scenarios |
| Methodology | SDD: PRD → ADRs → OpenSpec changes → Code |
| Spec language | English |
| Upstream docs | `docs/web/docs/` — canonical for SUMO user-facing behavior |
| Fork specs | `specs/` — canonical for this project's API and extracted architecture |

---

## Global context

This repository is **Eclipse SUMO used as a read-only engine**, plus a **new GIS API** we build on top. The product ingests GeoJSON, GeoPackage, SQLite, and OMX OD matrices, normalizes them in **new Python code**, and **orchestrates existing SUMO binaries** (`netconvert`, `polyconvert`, `od2trips`, `duarouter`, `sumo`) via `sumolib` — without modifying upstream `src/` or existing `tools/` files.

Methodology is **spec-driven development**: charter (`specs/prd.md`) → ADRs → OpenSpec changes → code only under **writable roots** (see § Architecture). Upstream behavior lives in `docs/web/docs/`; fork decisions live in `specs/`.

---

## Architecture

| Layer | Style | Doc |
|---|---|---|
| Upstream SUMO | Multi-binary toolkit, XML file pipeline, modular C++ | `specs/standards/architecture.md` § Upstream |
| Fork GIS API | Facade + subprocess orchestrator; read-only SUMO | `specs/standards/architecture.md` § Target |

**Before writing code:** read `specs/standards/architecture.md` and respect writable roots below.

### Writable roots (allowlist)

Everything under `src/` and existing `tools/` files is **read-only**. New code **only** here:

| Path | Purpose |
|---|---|
| `tools/import/gis/**` | GIS import, OMX adapter, API (ADR-009) |
| `tests/tools/import/gis/**` | Tests |
| `specs/**`, `ai/**`, `openspec/**` | Specs and AI meta |

`tools/import/gtfs/`, `tools/import/visum/`, `osmBuild.py`, `sumolib/`, etc. remain **upstream — do not edit**. Adding a writable root requires updating this table and `specs/standards/architecture.md`.

---

## Repository layout

```
project-root/
├── AGENTS.md                      ← this file (universal instructions)
├── CLAUDE.md                      ← Claude Code config (generated from ai/)
├── ai/                            ← canonical AI assets (source of truth)
│   ├── agents/                    ← agent/persona definitions
│   ├── commands/                  ← command/workflow definitions
│   ├── context/                   ← shared context fragments
│   └── scripts/                   ← utility scripts
├── scripts/
│   └── sync_ai.py                 ← generates platform files from ai/
├── specs/
│   ├── prd.md                     ← Product charter
│   ├── glossary.md                ← Domain glossary
│   ├── interfaces.md              ← Cross-module contract registry
│   ├── coverage.md                ← Context extraction schedule & ledger
│   ├── adr-registry.md            ← ADR status index (authoritative)
│   ├── adrs/                      ← Architecture Decision Records
│   └── standards/                 ← Coding standards (pointers + fork deltas)
├── openspec/
│   ├── config.yaml                ← OpenSpec project context + rules
│   ├── specs/                     ← Archived capabilities (post-archive)
│   └── changes/                   ← In-flight changes
├── .claude/                       ← Claude artifacts (generated + OpenSpec)
│   ├── agents/                    ← generated from ai/agents/
│   ├── commands/                  ← generated + OpenSpec opsx/
│   └── skills/openspec-*/         ← OpenSpec skills (DO NOT EDIT)
├── .cursor/                       ← Cursor artifacts (generated)
│   ├── rules/sumo-cursor.mdc
│   └── skills/                    ← generated from ai/commands/
├── src/                           ← C++ SUMO core (EPL derivative work)
├── tools/                         ← Python tools (existing = read-only)
│   └── import/
│       └── gis/                   ← FORK WRITABLE — new GIS API module (ADR-009)
├── data/                          ← XSD schemas, typemaps, emissions data
├── docs/                          ← Upstream documentation
└── tests/                         ← Regression tests
```

---

## Hard rules

1. **Brownfield first.** Extract architecture from existing code and `docs/web/docs/` before proposing changes. Tier A ADRs document as-built reality.
2. **Point, don't duplicate.** User-facing SUMO behavior is documented upstream; `specs/` synthesizes for this fork.
3. **Upstream read-only.** Do **not modify any existing file** under `src/` or `tools/`. Read and invoke via subprocess only. EPL applies if upstream files were ever edited — this project avoids that (see `src/README_Contributing.md`).
4. **Writable allowlist.** New implementation code **only** under paths in § Writable roots (`tools/import/gis/**`, matching tests, `specs/`, `ai/`, `openspec/`). Do not edit sibling packages (e.g. `tools/import/gtfs/`). Do not add files inside `sumolib/` or patch `osmBuild.py`.
5. **Spec-before-code in OpenSpec window.** After `/opsx:apply` and before `/opsx:archive`, update artifacts before code for new fix requests.
6. **Interface registry.** Cross-module contracts go in `specs/interfaces.md`; mark `unverified` until reconciliation.
7. **Do not edit generated AI files** (`.claude/agents/`, `.cursor/rules/`, `CLAUDE.md`) — edit `ai/` and run `python scripts/sync_ai.py`.
8. **Do not edit OpenSpec skills** under `.claude/skills/openspec-*`.
9. **OMX gap.** SUMO has no native OMX reader; demand from OMX requires ADR-012 adapter (see `specs/interfaces.md`).

---

## Active focus

Operational state lives in `specs/` — **not** duplicated in this file.

| What | Where |
|---|---|
| Next slice / extraction mode | [specs/coverage.md](specs/coverage.md) § Current focus |
| ADR status index | [specs/adr-registry.md](specs/adr-registry.md) |
| Tier B workshop checklist | [specs/workshop-tier-b.md](specs/workshop-tier-b.md) |

When a slice or ADR status changes, update those files (and the ADR file itself). Do not add tables back to `AGENTS.md`.

---

## OpenSpec workflow

This project uses OpenSpec for change management.

| Command | Purpose |
|---|---|
| `/opsx:propose <name>` | Start a new change |
| `/opsx:explore <topic>` | Think through an idea (read-only) |
| `/opsx:apply [<name>]` | Implement tasks from current change |
| `/opsx:archive [<name>]` | Finalize and merge a completed change |
| `/sumo-propose <name>` | Wrapper with SUMO pre-flight (after ai/ sync) |
| `/sumo-apply [<name>]` | Wrapper with in-flow guardrail |
| `/sumo-archive [<name>]` | Wrapper with spec guard gate |
| `/check-spec <name>` | Ad-hoc audit against specs |

### Post-apply discipline

When a fix arrives after `/opsx:apply` and before `/opsx:archive`:

1. Update OpenSpec artifacts (proposal, design, tasks, delta spec) first.
2. Implement code only after artifacts reflect the request.
3. Re-verify before archiving.

---

## Agent personas

| Persona | Activation phrase | Use when |
|---|---|---|
| **Codebase Analyst** | `Act as Codebase Analyst for <slice>` | Extracting architecture from a folder/slice |
| **Reconcile Reviewer** | `Act as Reconcile Reviewer` | Cross-slice glossary/interface consistency |
| **SUMO Spec Guard** | `Act as SUMO Spec Guard for <change-name>` | Auditing OpenSpec changes against specs |

Full persona definitions: `ai/agents/` (canonical source).

---

## On-demand reading order

1. `specs/standards/architecture.md` — upstream vs fork, writable roots (**before coding**)
2. `specs/coverage.md` — if doing context extraction (§ Current focus)
3. `specs/adr-registry.md` — which ADRs exist and their status
4. `specs/prd.md` — product charter and MVP scope
5. `specs/glossary.md` — locked domain terms
6. Relevant `specs/adrs/ADR-NNN-*.md` — decision detail
7. `specs/standards/` — coding conventions
8. `specs/interfaces.md` — cross-module contracts
9. `openspec/config.yaml` — OpenSpec artifact rules (when using `/opsx:*`)
10. Upstream `docs/web/docs/` — user-facing SUMO behavior

---

## AI configuration layer

Canonical AI assets live in `ai/`. Platform artifacts are **generated**.

| Action | Command |
|---|---|
| Regenerate all | `python scripts/sync_ai.py` |
| Validate (no write) | `python scripts/sync_ai.py --check` |
| Cursor only | `python scripts/sync_ai.py --cursor` |
| Claude only | `python scripts/sync_ai.py --claude` |

When adding or modifying an agent, command, or context fragment, edit `ai/` and run the generator.

---

## Coding standards

ADRs decide architecture. Standards sit one layer below.

| File | Scope |
|---|---|
| `specs/standards/architecture.md` | Upstream vs fork, writable roots, integration style |
| `specs/standards/cpp-standards.md` | C++ — points to upstream CodeStyle (read-only `src/`) |
| `specs/standards/python-standards.md` | Python — `tools/import/gis/` conventions |
| `specs/standards/api-standards.md` | HTTP API conventions (after ADR-010) |
| `specs/standards/spec-writing.md` | How to write specs and ADRs |
