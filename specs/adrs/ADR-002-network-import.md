# ADR-002: Network Import Pipeline

**Status:** Accepted (documented from code)
**Tier:** A
**Sources:** `src/netimport/`, `src/netbuild/`, `docs/web/docs/netconvert.md`

## Context

The GIS API must produce `.net.xml` from spatial line data. SUMO's network import is centralized in `netconvert`.

## Decision

**As-built pipeline:**

1. `NIFrame.cpp` registers input options (`--osm-files`, `--shapefile-prefix`, etc.).
2. `NILoader.cpp` dispatches importers in order: SUMO net, OSM, VISUM, **ArcView/shapefile**, OpenDRIVE, others, then plain XML.
3. `NIImporter_ArcView.cpp` reads shapefiles via GDAL/OGR — **LineString only**; requires column mapping (`shapefile.from-id`, `shapefile.to-id`, `shapefile.street-id`, `shapefile.type-id`, etc.).
4. `NIImporter_OpenStreetMap.cpp` handles native OSM XML (best-documented path).
5. `netbuild` prepares topology; output written as `.net.xml`.

**Gaps for MVP:**

| Format | Network import | Notes |
|---|---|---|
| OSM | Yes | Reference: `osmBuild.py` |
| Shapefile | Yes | Schema-specific; see [ArcView.md](../../docs/web/docs/Networks/Import/ArcView.md) |
| GeoJSON | **No** | Export only (`tools/net/net2geojson.py`); API must preprocess |
| GPKG | **No** | No dedicated importer; extract lines → shapefile-like or XML |
| SQLite | **No** | API normalization required |

## Consequences

- API normalization layer (ADR-011) must convert GeoJSON/GPKG/SQLite line layers into a netconvert-accepted form.
- Do not assume generic "any line layer" works with shapefile importer without schema mapping.

## References

- PRD §2, §5
- `specs/interfaces.md` — Network row
