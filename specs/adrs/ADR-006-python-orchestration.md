# ADR-006: Python Orchestration Pattern

**Status:** Draft (documented from code)
**Tier:** A
**Sources:** `tools/osmBuild.py`, `tools/osmWebWizard.py`, `tools/sumolib/`

## Context

The GIS API orchestrates SUMO binaries rather than reimplementing import logic. `osmBuild.py` is the canonical single-format orchestration reference.

## Decision

**As-built pattern (`osmBuild.py`):**

1. Parse options via `sumolib.options.ArgumentParser`.
2. Resolve binaries: `sumolib.checkBinary('netconvert', bindir)`, `polyconvert`.
3. Build option lists from comma-separated defaults (`DEFAULT_NETCONVERT_OPTS`).
4. Early validation: input file exists, output directory exists, vehicle class valid.
5. Run `netconvert` with `--save-configuration` → `.netccfg`, then `netconvert -c`.
6. If typemap provided: run `polyconvert` similarly → `.polycfg`, output `.poly.xml`.
7. Use `cwd=output_directory` with relative paths via `getRelative()`.

**Key defaults:**

```python
DEFAULT_NETCONVERT_OPTS = (
    '--geometry.remove,--ramps.guess,--junctions.join,'
    '--tls.guess-signals,--tls.discard-simple,--tls.join,--output.original-names,'
    '--output.street-names'
)
```

**Not in osmBuild (API must add):**

- od2trips, duarouter, OMX adapter, GIS normalization, HTTP layer.
- `osmWebWizard.py` adds demand generation and GUI launch — broader scenario template.

**sumolib responsibilities:**

- Binary discovery (`SUMO_HOME`, `bindir`)
- Options parsing
- Subprocess orchestration (caller's responsibility)

## Consequences

- New API orchestrator follows osmBuild structure: validate → config files → subprocess → artifacts.
- Extend with demand pipeline steps per `specs/interfaces.md` target sequence.

## References

- PRD §1, §5
- OpenSpec change: `document-orchestration-slice`
