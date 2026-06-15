# ADR-011: GIS Normalization Layer

**Status:** Draft — **workshop required**
**Tier:** B
**Blocks:** GeoJSON/GPKG/SQLite network path

## Context

ADR-002 documents gaps: no native GeoJSON/GPKG/SQLite network import. API must normalize before calling netconvert/polyconvert.

## Options

| Option | Approach |
|---|---|
| **A** | Python `pyogrio`/`geopandas` → extract layers → write temp GeoJSON/shapefile → invoke binaries |
| **B** | GDAL CLI (`ogr2ogr`) preprocessing |
| **C** | Extend polyconvert/netconvert C++ (out of scope v1) |
| **D** | Hybrid: geopandas for inspection + shapefile export for netconvert |

## CRS policy (must decide)

- Auto-detect from source vs require client-supplied EPSG?
- Always reproject to network CRS before netconvert?
- Log all transforms (PRD §4)?

## Decision

**Pending workshop.**

Recommendation: **Option A/D** — Python normalization in API service, reuse SUMO binaries unchanged.

## Consequences

- Python dependencies: geopandas, pyogrio, pyproj (add to API requirements).
- ADR-004 GDAL in SUMO build still required for polyconvert path.

## References

- ADR-002, ADR-003
- PRD §2, §4
