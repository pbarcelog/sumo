# Tier B ADR Workshop — Decision Checklist

**Purpose:** Gate first API implementation OpenSpec change.
**Status:** **Complete** — 2026-06-16 (Pablo workshop)

---

## ADR-008 API Stack

- [x] Framework: **FastAPI**
- [x] Job model: **asyncio background tasks** + filesystem job status
- [x] Packaging: **Docker**

## ADR-009 Code Placement

- [x] Path: **`tools/import/gis/**`** (Accepted 2026-06-15)
- [x] Tests: **`tests/tools/import/gis/**`**
- [x] Upstream contribution intent: **fork-only** (v1)

## ADR-010 API Contract

- [x] Approve draft REST resources in ADR-010
- [x] Max upload size: **500 MB** per file
- [x] GPKG layer selection: **`?layer=`** query parameter
- [x] Auth deferred to v2: **yes**

## ADR-011 GIS Normalization

- [x] Library: **geopandas + pyogrio**
- [x] CRS policy: **auto-detect**; client EPSG override; **reproject to network CRS**; log transforms

## ADR-012 OMX Adapter

- [x] Output format: **tazRelation XML**
- [x] Library: **openmatrix**
- [x] Time slice mapping: **OMX slices → tazRelation `interval`**; vehicle type from OMX metadata when present

## ADR-013 SQLite Role

- [x] SpatiaLite geometry: **yes**
- [x] Plain attribute tables: **yes** (join by key)
- [x] Schema conventions: **`zone_id` / `id`**, `build_options.sqlite_joins` — see ADR-013

## ADR-014 TAZ Derivation

- [x] OMX zone ids must match TAZ/polygon ids: **strict** (Option A)
- [x] Polygon source layer name convention: **`zones`** (override via `?layer=` / build_options)
- [x] Fuzzy centroid-in-polygon matching: **deferred v2**

## ADR-015 Simulation Execution

- [x] Execution: **subprocess sumo** (Option A)
- [x] Artifact storage: **local filesystem** per scenario id

---

## After workshop

1. [x] Update each ADR status to **Accepted** with decision recorded.
2. [x] Update [specs/adr-registry.md](adr-registry.md) and each ADR file.
3. [x] Activate `specs/standards/api-standards.md`.
4. [x] Propose first implementation OpenSpec change: **`gis-api-mvp`** (2026-06-16).
