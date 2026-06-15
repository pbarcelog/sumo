# ADR-003: Shape and POI Import (polyconvert)

**Status:** Draft (documented from code)
**Tier:** A
**Sources:** `src/polyconvert/`, `docs/web/docs/polyconvert.md`

## Context

Non-network geometry (TAZ polygons, POIs, buildings) flows through `polyconvert`, separate from `netconvert`.

## Decision

**As-built loaders** (`polyconvert_main.cpp` dispatch order):

XML → OSM → DlrNavteq → VISUM → **ArcView** (shapefile + GeoJSON).

`PCLoaderArcView.cpp`:
- Triggered by `--shapefile-prefixes` (appends `.shp`) or `--geojson-files`.
- Uses GDAL `GDALOpenEx` when `HAVE_GDAL` is defined.
- Supports Point, Polygon, LineString, Multi* → POIs/polygons.
- Without GDAL: emits *"compiled without GDAL support"*.

**GPKG hypothesis (unverified):**

Same GDAL loader may open `.gpkg` if passed to `--geojson-files` path (GDALOpenEx). Not documented or tested in SUMO. Mark **unverified** until regression test exists.

## Consequences

- TAZ polygons from GIS likely route through polyconvert or `edgesInDistricts.py` (ADR-014).
- API must not conflate polyconvert output with network files.

## References

- PRD §2
- Tests: `tests/polyconvert/import/geojson/`, `tests/polyconvert/import/shape/`
