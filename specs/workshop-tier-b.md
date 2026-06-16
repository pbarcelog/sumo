# Tier B ADR Workshop — Decision Checklist

**Purpose:** Gate first API implementation OpenSpec change.
**Status:** **Next** — context extraction complete (R2); awaiting Pablo's decisions

Work through each ADR in order. Record decision and date in the ADR file when accepted.

---

## ADR-008 API Stack

- [ ] Framework: FastAPI (recommended) / Flask / other: ___________
- [ ] Job model: sync / asyncio background / Celery+Redis: ___________
- [ ] Packaging: Docker / bare metal: ___________

## ADR-009 Code Placement

- [x] Path: **`tools/import/gis/**`** (Accepted 2026-06-15) — see ADR-009
- [x] Tests: **`tests/tools/import/gis/**`**
- [ ] Upstream contribution intent: fork-only / eventual PR

## ADR-010 API Contract

- [ ] Approve draft REST resources in ADR-010
- [ ] Max upload size: ___________
- [ ] GPKG layer selection mechanism: ___________
- [ ] Auth deferred to v2: yes / no

## ADR-011 GIS Normalization

- [ ] Library: geopandas+pyogrio / GDAL CLI / hybrid
- [ ] CRS policy: auto-detect / client EPSG required / always reproject to: ___________

## ADR-012 OMX Adapter

- [ ] Output format: tazRelation XML (recommended) / VISUM V-format
- [ ] Library: openmatrix / other: ___________
- [ ] Time slice mapping rules: ___________

## ADR-013 SQLite Role

- [ ] SpatiaLite geometry: yes / no
- [ ] Plain attribute tables: yes / no
- [ ] Required schema conventions: ___________

## ADR-014 TAZ Derivation

- [ ] OMX zone ids must match TAZ ids: strict / auto-join / client supplies tazs
- [ ] Polygon source layer name convention: ___________

## ADR-015 Simulation Execution

- [ ] Execution: subprocess sumo (recommended) / TraCI socket / libsumo or libtraci (Option D)
- [ ] Artifact storage: local filesystem / object storage

---

## After workshop

1. Update each ADR status to **Accepted** with decision recorded.
2. Update [specs/adr-registry.md](adr-registry.md) and each ADR file.
3. Activate `specs/standards/api-standards.md`.
4. Propose first implementation OpenSpec change (e.g. `gis-api-mvp`).
