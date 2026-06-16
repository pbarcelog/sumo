# ADR-012: OMX Adapter

**Status:** Accepted
**Tier:** B
**Date:** 2026-06-16

## Context

OMX (Open Matrix) is the MVP OD matrix format. SUMO has **no native OMX reader** (ADR-005). An adapter must convert OMX → SUMO-accepted format.

## Options considered

| Option | Output | Library |
|---|---|---|
| **A** | tazRelation XML | Python `openmatrix` → emit `datamode_file.xsd` XML |
| **B** | VISUM V-format | `openmatrix` → text V-format for `ODMatrix.cpp` |
| **C** | Direct trips.xml | Skip od2trips; generate trips programmatically (loses OD tooling) |

## Decision

**Output format:** **tazRelation XML** (Option A) — validates against ADR-007 XSD; preserves od2trips → duarouter pipeline.

**Library:** Python **`openmatrix`** in `tools/import/gis/omx/`.

**Time slices:** Map each OMX matrix (or named slice) to a **`tazRelation` `interval`** attribute. Single-matrix OMX files produce one interval; multi-slice OMX produces one relation set per slice with interval metadata from OMX attributes when present.

**Vehicle type:** When OMX core or file metadata specifies vehicle type, map to SUMO `vType` on relations; otherwise default to a single passenger car type defined in build options.

**Multiple matrices:** Process all non-empty matrices in one OMX file; reject if slice names collide or dimensions disagree with TAZ count (ADR-014).

## Consequences

- Module: `tools/import/gis/omx/`.
- Unit tests: OMX fixture → tazRelation XML → od2trips round-trip under `tests/tools/import/gis/`.
- `specs/interfaces.md` OMX row moves from `gap` to `partial` when adapter lands.

## References

- ADR-005, ADR-007, ADR-014
- `specs/interfaces.md` — OMX gap
- `tools/route/route2OD.py` (inverse for testing)
