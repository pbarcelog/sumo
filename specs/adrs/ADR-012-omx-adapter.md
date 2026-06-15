# ADR-012: OMX Adapter

**Status:** Draft — **workshop required**
**Tier:** B
**Blocks:** OMX demand path (PRD §2 MVP)

## Context

OMX (Open Matrix) is the MVP OD matrix format. SUMO has **no native OMX reader** (ADR-005). An adapter must convert OMX → SUMO-accepted format.

## Options

| Option | Output | Library |
|---|---|---|
| **A** | tazRelation XML | Python `openmatrix` → emit `datamode_file.xsd` XML |
| **B** | VISUM V-format | `openmatrix` → text V-format for `ODMatrix.cpp` |
| **C** | Direct trips.xml | Skip od2trips; generate trips programmatically (loses OD tooling) |

## Recommendation

**Option A** — tazRelation XML:

- Validates against existing XSD (ADR-007).
- Preserves od2trips / duarouter pipeline.
- `tools/route/route2OD.py` provides inverse for testing.

## Open questions

- OMX time slices → tazRelation `interval` mapping?
- Vehicle type from OMX cores?
- Multiple matrices in one OMX file?

## Decision

**Pending workshop.**

## Consequences

- New module in API placement (ADR-009).
- Unit tests: OMX fixture → tazRelation → od2trips round-trip.

## References

- ADR-005, ADR-014
- `specs/interfaces.md` — OMX gap
