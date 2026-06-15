#!/usr/bin/env python3
"""
SUMO GIS API AI sync — generates platform-specific artifacts from canonical ai/ sources.

Usage:
    python scripts/sync_ai.py              # generate all
    python scripts/sync_ai.py --check      # verify files are up-to-date (exit 1 if stale)
    python scripts/sync_ai.py --cursor     # generate Cursor artifacts only
    python scripts/sync_ai.py --claude     # generate Claude artifacts only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
AI_DIR = ROOT / "ai"
GENERATED_HEADER = (
    "<!-- GENERATED FILE — DO NOT EDIT DIRECTLY.\n"
    "     Source: ai/ directory.  Regenerate: python scripts/sync_ai.py -->"
)
GENERATED_HEADER_HASH = (
    "# GENERATED FILE — DO NOT EDIT DIRECTLY.\n"
    "# Source: ai/ directory.  Regenerate: python scripts/sync_ai.py"
)
GENERATED_HEADER_JSON_KEY = "__generated"
GENERATED_HEADER_JSON_VAL = "DO NOT EDIT. Source: ai/. Regenerate: python scripts/sync_ai.py"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Return (metadata_dict, markdown_body) from a file with YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    body = text[m.end():]
    return meta, body


def load_all(subdir: str) -> list[dict]:
    """Load all .md files from ai/<subdir>/, returning sorted list of dicts
    with keys: meta, body, filename."""
    folder = AI_DIR / subdir
    if not folder.is_dir():
        return []
    items = []
    for p in sorted(folder.glob("*.md")):
        meta, body = parse_frontmatter(p)
        items.append({"meta": meta, "body": body, "filename": p.stem})
    return items


def load_context(name: str) -> str:
    """Load ai/context/<name>.md as raw text, stripped."""
    p = AI_DIR / "context" / name
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8").strip()


def write_if_changed(path: Path, content: str, *, check: bool) -> bool:
    """Write content to path. In check mode, return True if file would change."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return False
    if check:
        return True
    path.write_text(content, encoding="utf-8")
    return False

# ---------------------------------------------------------------------------
# Tool mappings
# ---------------------------------------------------------------------------

CLAUDE_TOOL_MAP = {
    "filesystem": "Read, Grep, Glob, Write, Edit",
    "search": "Grep, Glob",
    "shell": "Bash",
}

CLAUDE_MODEL_MAP = {
    "high-reasoning": "opus",
    "any": None,
}

# ---------------------------------------------------------------------------
# Claude generators
# ---------------------------------------------------------------------------

def _short_desc(description: str) -> str:
    """Extract the first sentence, splitting on '. ' to avoid cutting 'AGENTS.md'."""
    parts = re.split(r"\.\s", description, maxsplit=1)
    return parts[0].rstrip(".")


def generate_claude_agent(agent: dict) -> str:
    meta = agent["meta"]
    body = agent["body"]

    tools_generic = meta.get("tools", [])
    tools_claude = ", ".join(
        CLAUDE_TOOL_MAP.get(t, t) for t in tools_generic
    )
    # Deduplicate tool list
    seen = []
    for t in tools_claude.split(", "):
        if t not in seen:
            seen.append(t)
    tools_claude = ", ".join(seen)

    model = CLAUDE_MODEL_MAP.get(meta.get("model_preference", "any"), None)

    lines = [GENERATED_HEADER, "", "---"]
    lines.append(f"name: {meta['name']}")
    lines.append(f"description: {meta['description']}")
    lines.append(f"tools: {tools_claude}")
    if model:
        lines.append(f"model: {model}")
    lines.append("---")
    lines.append(body.rstrip())
    lines.append("")
    return "\n".join(lines)


def generate_claude_command(cmd: dict) -> str:
    meta = cmd["meta"]
    body = cmd["body"]

    lines = [GENERATED_HEADER, "", "---"]
    lines.append(f"description: {meta['description']}")
    arg = meta.get("argument")
    if arg and arg != "null":
        lines.append(f"argument-hint: {arg}")
    lines.append("---")

    # Transform generic language to Claude-specific
    claude_body = body.rstrip()
    claude_body = claude_body.replace(
        "ask the user", "ask the user (via $ARGUMENTS or interactively)"
    )

    lines.append(claude_body)
    lines.append("")
    return "\n".join(lines)


def generate_claude_md(agents: list[dict], commands: list[dict]) -> str:
    model_guidance = load_context("model-guidance.md")
    key_files = load_context("key-files.md")
    git_conventions = load_context("git-conventions.md")

    # Build agent table
    agent_rows = []
    for a in agents:
        m = a["meta"]
        desc = _short_desc(m["description"])
        agent_rows.append(
            f"| `{m['name']}.md` | {desc} "
            f"| `{m.get('activation_phrase', '')}` |"
        )
    agent_table = "\n".join(agent_rows)

    # Build command table
    cmd_rows = []
    for c in commands:
        m = c["meta"]
        arg = m.get("argument", "")
        arg_display = f" {arg}" if arg and arg != "null" else ""
        desc = _short_desc(m["description"])
        cmd_rows.append(
            f"| `/{m['name']}{arg_display}` | {desc} |"
        )
    cmd_table = "\n".join(cmd_rows)

    return f"""{GENERATED_HEADER}

# SUMO GIS API — Claude Code Configuration

See `AGENTS.md` for the full project context, domain glossary, ADR status, and hard rules.
This file contains only Claude Code-specific additions.

---

## Model guidance

{model_guidance}

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
{cmd_table}

---

## Subagents

Subagent definitions live in `.claude/agents/`. Each file = one persona.
Invoke via the activation phrase from `AGENTS.md`, via a slash command, or via the Agent tool.

| File | Purpose | Activation phrase |
| --- | --- | --- |
{agent_table}

---

## Hooks

`SessionStart` runs `ai/scripts/session-start.ps1` (PowerShell 5.1+) on session start and resume.
Output: current branch, ADR inventory with status, uncommitted spec changes, and a reminder of the available agents/commands.
Disable by removing the `hooks` block from `.claude/settings.local.json`.

---

## Key file paths

{key_files}

---

## Git conventions

{git_conventions}
"""


def generate_claude_settings() -> str:
    # Key order MUST match what Claude Code's permission engine produces
    # when it auto-accepts a new permission and re-serialises the file:
    # permissions first, then hooks, then __generated. Any other order
    # makes sync_ai.py --check fail right after the engine touches the
    # file (e.g. when accepting a permission for the very command the
    # pre-commit hook invokes).
    obj = {
        "permissions": {
            "allow": [
                "WebFetch(domain:github.com)",
                "WebFetch(domain:raw.githubusercontent.com)",
                "WebFetch(domain:api.github.com)",
                # OpenSpec read-only surface — frequently exercised by the
                # /opsx:* and /next-adr workflows. Mutating subcommands
                # (`new`, `archive`, `apply`) are intentionally NOT
                # allowlisted so they keep prompting.
                "Bash(openspec --version)",
                "Bash(openspec --help)",
                "Bash(openspec status *)",
                "Bash(openspec instructions *)",
                "Bash(openspec validate *)",
                "Bash(openspec schemas *)",
                "Bash(python scripts/sync_ai.py --check)",
                "Bash(python scripts/sync_ai.py)",
                "Bash(git add *)",
                "Bash(git commit -m ' *)",
                "Bash(git status)",
                "Bash(git diff *)",
                "Bash(git log *)",
            ]
        },
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                "powershell -NoProfile -ExecutionPolicy Bypass "
                                "-File ai/scripts/session-start.ps1"
                            ),
                        }
                    ],
                }
            ]
        },
        GENERATED_HEADER_JSON_KEY: GENERATED_HEADER_JSON_VAL,
    }
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Cursor generators
# ---------------------------------------------------------------------------

def generate_cursor_skill(cmd: dict) -> str:
    meta = cmd["meta"]
    body = cmd["body"]

    agent = meta.get("invokes_agent")

    # Transform generic language to Cursor-specific
    cursor_body = body.rstrip()
    if agent and agent != "null":
        cursor_body = cursor_body.replace(
            f"Launch the `{agent}` agent",
            f"Launch the `{agent}` agent using the `Task` tool "
            f'with `subagent_type: "{agent}"`',
        )

    cursor_body = cursor_body.replace(
        "ask the user",
        "use the `AskQuestion` tool to ask the user"
    )

    lines = [GENERATED_HEADER, "", "---"]
    lines.append(f"name: {meta['name']}")
    lines.append(f"description: >-")
    lines.append(f"  {meta['description']}")
    lines.append("---")
    lines.append(cursor_body)
    lines.append("")
    return "\n".join(lines)


def generate_cursor_rule(agents: list[dict], commands: list[dict]) -> str:
    model_guidance = load_context("model-guidance.md")
    key_files = load_context("key-files.md")
    git_conventions = load_context("git-conventions.md")

    # Build agent table
    agent_rows = []
    for a in agents:
        m = a["meta"]
        desc = _short_desc(m["description"])
        agent_rows.append(
            f"| `{m['name']}` | {desc} "
            f"| `{m.get('activation_phrase', '')}` |"
        )
    agent_table = "\n".join(agent_rows)

    # Build skill table
    skill_rows = []
    for c in commands:
        m = c["meta"]
        desc = _short_desc(m["description"])
        skill_rows.append(
            f"| `{m['name']}` | {desc} |"
        )
    skill_table = "\n".join(skill_rows)

    return f"""{GENERATED_HEADER}

---
description: SUMO GIS API project — Cursor-specific configuration. Complements AGENTS.md (universal rules).
alwaysApply: true
---

# SUMO GIS API — Cursor Configuration

See `AGENTS.md` for the full project context, domain glossary, ADR status, and hard rules.
This file contains only Cursor-specific additions.

---

## Model guidance

{model_guidance}

---

## Tool name mapping

Some skill files (inherited from `.claude/skills/`) reference `AskUserQuestion`.
In Cursor this tool is called `AskQuestion` — treat them as equivalent.

---

## Skills

### OpenSpec skills (managed by OpenSpec — do not edit)

These live in `.claude/skills/` and are auto-detected by Cursor:

| Skill | Trigger | Purpose |
|---|---|---|
| `openspec-propose` | User wants to start a new change | Creates proposal, design, and tasks artifacts |
| `openspec-explore` | User wants to think through an idea | Free-form exploration mode, no implementation |
| `openspec-apply-change` | User wants to implement tasks | Reads task list and implements sequentially |
| `openspec-archive-change` | User wants to finalize a change | Checks completion, syncs specs, archives |

### Custom skills (in `.cursor/skills/`)

| Skill | Purpose |
|---|---|
{skill_table}

---

## Subagents

Subagent personas are registered as Cursor subagent types.
Invoke via the `Task` tool with the appropriate `subagent_type`, or via activation phrases from `AGENTS.md`.

| `subagent_type` | Persona | Activation phrase |
|---|---|---|
{agent_table}

---

## Hooks

`sessionStart` runs `ai/scripts/session-start.ps1` (PowerShell 5.1+) on every session start.
Output: current branch, ADR inventory with status, uncommitted spec changes, and a reminder of available agents and skills.
Configuration: `.cursor/hooks.json`.

---

## Key file paths

{key_files}

---

## Git conventions

{git_conventions}
"""


def generate_cursor_hooks() -> str:
    obj = {
        GENERATED_HEADER_JSON_KEY: GENERATED_HEADER_JSON_VAL,
        "version": 1,
        "hooks": {
            "sessionStart": [
                {
                    "command": (
                        "powershell -NoProfile -ExecutionPolicy Bypass "
                        "-File ai/scripts/session-start.ps1"
                    )
                }
            ]
        },
    }
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run(*, check: bool = False, cursor: bool = True, claude: bool = True) -> int:
    agents = load_all("agents")
    commands = load_all("commands")

    stale: list[str] = []

    if claude:
        # CLAUDE.md
        content = generate_claude_md(agents, commands)
        if write_if_changed(ROOT / "CLAUDE.md", content, check=check):
            stale.append("CLAUDE.md")

        # .claude/agents/
        for agent in agents:
            p = ROOT / ".claude" / "agents" / f"{agent['filename']}.md"
            content = generate_claude_agent(agent)
            if write_if_changed(p, content, check=check):
                stale.append(str(p.relative_to(ROOT)))

        # .claude/commands/ (only our custom commands, not opsx/)
        for cmd in commands:
            p = ROOT / ".claude" / "commands" / f"{cmd['filename']}.md"
            content = generate_claude_command(cmd)
            if write_if_changed(p, content, check=check):
                stale.append(str(p.relative_to(ROOT)))

        # .claude/settings.local.json
        content = generate_claude_settings()
        if write_if_changed(
            ROOT / ".claude" / "settings.local.json", content, check=check
        ):
            stale.append(".claude/settings.local.json")

    if cursor:
        # .cursor/rules/sumo-cursor.mdc
        content = generate_cursor_rule(agents, commands)
        if write_if_changed(
            ROOT / ".cursor" / "rules" / "sumo-cursor.mdc", content, check=check
        ):
            stale.append(".cursor/rules/sumo-cursor.mdc")

        # .cursor/skills/
        for cmd in commands:
            p = ROOT / ".cursor" / "skills" / cmd["filename"] / "SKILL.md"
            content = generate_cursor_skill(cmd)
            if write_if_changed(p, content, check=check):
                stale.append(str(p.relative_to(ROOT)))

        # .cursor/hooks.json
        content = generate_cursor_hooks()
        if write_if_changed(ROOT / ".cursor" / "hooks.json", content, check=check):
            stale.append(".cursor/hooks.json")

    if check and stale:
        print("STALE — the following generated files need regeneration:", file=sys.stderr)
        for s in stale:
            print(f"  {s}", file=sys.stderr)
        print("\nRun: python scripts/sync_ai.py", file=sys.stderr)
        return 1

    if not check:
        generated = []
        if claude:
            generated.extend([
                "CLAUDE.md",
                *[f".claude/agents/{a['filename']}.md" for a in agents],
                *[f".claude/commands/{c['filename']}.md" for c in commands],
                ".claude/settings.local.json",
            ])
        if cursor:
            generated.extend([
                ".cursor/rules/sumo-cursor.mdc",
                *[f".cursor/skills/{c['filename']}/SKILL.md" for c in commands],
                ".cursor/hooks.json",
            ])
        print(f"Generated {len(generated)} files from ai/:")
        for g in generated:
            print(f"  {g}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate platform-specific AI config from canonical ai/ sources."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify generated files are up-to-date without writing (exit 1 if stale).",
    )
    parser.add_argument(
        "--cursor",
        action="store_true",
        help="Generate Cursor artifacts only.",
    )
    parser.add_argument(
        "--claude",
        action="store_true",
        help="Generate Claude Code artifacts only.",
    )
    args = parser.parse_args()

    # If neither --cursor nor --claude specified, generate both
    do_cursor = args.cursor or (not args.cursor and not args.claude)
    do_claude = args.claude or (not args.cursor and not args.claude)

    sys.exit(run(check=args.check, cursor=do_cursor, claude=do_claude))


if __name__ == "__main__":
    main()
