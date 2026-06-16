# Python Coding Standards — SUMO GIS API Fork

## Canonical upstream (do not duplicate)

| Topic | Location |
|---|---|
| Python template | [docs/web/docs/Developer/PythonFileTemplate.md](../../docs/web/docs/Developer/PythonFileTemplate.md) |
| tools contributing | [tools/README_Contributing.md](../../tools/README_Contributing.md) |
| sumolib usage | [docs/web/docs/Tools/Sumolib.md](../../docs/web/docs/Tools/Sumolib.md) |

## Fork delta (API and orchestration modules)

**Package root:** `tools/import/gis/` (ADR-009). Do not add code to existing `tools/import/*` siblings or `sumolib/`.

- Use `sumolib.options.ArgumentParser` for CLI entry points.
- Resolve binaries via `sumolib.checkBinary(name, bindir)` — respect `SUMO_HOME`.
- Type hints on public API module functions (ADR-009 placement).
- SPDX license header on new files (match upstream EPL-2.0 OR GPL-2.0-or-later pattern).
- Orchestration: save `.netccfg` / `.polycfg` for reproducibility (osmBuild pattern).
- Subprocess calls: use `cwd=output_directory` with relative paths where possible.
- Tests: follow `specs/test-strategy.md` — TextTest under `tests/tools/import/gis/**`; resolve binaries via `checkBinary`.

## API modules (after ADR-008/010)

See `specs/standards/api-standards.md` for HTTP-specific conventions.
