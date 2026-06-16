# ADR-011: GIS Normalization Layer

**Status:** Accepted
**Tier:** B
**Date:** 2026-06-16

## Context

ADR-002 documents gaps: no native GeoJSON/GPKG/SQLite network import. API must normalize before calling netconvert/polyconvert.

## Options considered

| Option | Approach |
|---|---|
| **A** | Python `pyogrio`/`geopandas` → extract layers → write temp GeoJSON/shapefile → invoke binaries |
| **B** | GDAL CLI (`ogr2ogr`) preprocessing |
| **C** | Extend polyconvert/netconvert C++ (out of scope v1) |
| **D** | Hybrid: geopandas for inspection + shapefile export for netconvert |

## Decision

**Library:** **geopandas + pyogrio** in `tools/import/gis/normalize/` (Option A). Export to formats netconvert/polyconvert accept (shapefile, GeoJSON) before subprocess invocation. No C++ changes.

**CRS policy:**

1. **Auto-detect** CRS from source when present (GeoPackage, GeoJSON `crs`, SpatiaLite metadata).
2. Client MAY supply EPSG in `build_options.crs` to override or disambiguate.
3. **Always reproject** to the network CRS before netconvert when building road geometry.
4. **Log every transform** applied (PRD §4 quality bar).

## Consequences

- Python dependencies: `geopandas`, `pyogrio`, `pyproj` in API container image.
- ADR-004 GDAL in SUMO build still required for polyconvert upstream path.
- GPKG via pyogrio remains **unverified** until fork integration tests pass; failures must be explicit.

## References

- ADR-002, ADR-003, ADR-013
- PRD §2, §4
