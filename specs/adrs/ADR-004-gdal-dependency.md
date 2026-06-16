# ADR-004: GDAL Build Dependency

**Status:** Accepted (documented from code)
**Tier:** A
**Sources:** `CMakeLists.txt`, `src/polyconvert/CMakeLists.txt`

## Context

GIS format support in SUMO depends on optional GDAL at compile time.

## Decision

**As-built:**

- CMake option: `ENABLE_GDAL` (default tied to `CHECK_OPTIONAL_LIBS`).
- When enabled: `HAVE_GDAL` defined; `polyconvert` links GDAL.
- `netimport` shapefile path (`NIImporter_ArcView.cpp`) also uses GDAL/OGR.
- Heightmaps: `--heightmap.shapefiles`, `--heightmap.geotiff` in `NBHeightMapper.cpp`.

**Without GDAL:** shapefile, GeoJSON import, and geotiff heightmaps unavailable.

Install notes: [Linux_Build.md](../../docs/web/docs/Installing/Linux_Build.md).

## Consequences

- GIS API deployment must require GDAL-enabled SUMO build for MVP formats.
- API layer may additionally use Python GDAL/geopandas (ADR-011) independent of SUMO build.

## References

- PRD §4 (fail loud on GDAL errors)
