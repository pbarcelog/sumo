# Domain Glossary — SUMO GIS API

Locked terms for specs, ADRs, and OpenSpec artifacts. Update during slice passes and reconciliation.

| Term | Definition |
|---|---|
| **SUMO** | Simulation of Urban MObility — microscopic traffic simulation (Eclipse). |
| **Scenario** | Complete runnable simulation package: network, optional shapes, demand, routes, config. |
| **Network** | Road graph as `.net.xml` produced by `netconvert`. |
| **netconvert** | C++ tool: import/build SUMO networks from OSM, shapefile, OpenDRIVE, etc. |
| **polyconvert** | C++ tool: import shapes and POIs from OSM, GeoJSON, shapefile (GDAL). |
| **TAZ** | Traffic Analysis Zone — district for OD demand; defined in `tazs` XML. |
| **tazRelation** | SUMO XML format for OD flows between TAZs per time interval. |
| **od2trips** | C++ tool: converts OD matrices to trip definitions. |
| **duarouter** | C++ tool: assigns routes to trips. |
| **sumo** | C++ simulator executable. |
| **TraCI** | Traffic Control Interface — runtime API to control simulation. |
| **sumolib** | Python library for SUMO file I/O and binary invocation. |
| **typemap** | XML mapping external feature types to SUMO edge/shape types (`data/typemap/`). |
| **CRS** | Coordinate Reference System; projection handling via `GeoConvHelper` / API layer. |
| **GDAL** | Geospatial Data Abstraction Library; optional SUMO build dependency. |
| **GeoJSON** | JSON geographic format; polyconvert import via `--geojson-files`; network import **not** native. |
| **GPKG** | GeoPackage; multi-layer spatial SQLite container; **unverified** in SUMO — likely via GDAL in polyconvert. |
| **OMX** | Open Matrix — standard format for OD matrices; **not** natively read by SUMO; requires adapter (ADR-012). |
| **VISUM V-format** | PTV matrix format read by `ODMatrix.cpp`; alternative OMX adapter target. |
| **Orchestrator** | Python layer invoking SUMO binaries in sequence (pattern: `osmBuild.py`). Lives in fork: `tools/import/gis/`. |
| **Writable root** | Path allowlisted for new code (`tools/import/gis/**`); rest of `src/` and `tools/` is read-only. |
| **Slice** | Incremental documentation pass over a codebase area (see `specs/coverage.md` § Current focus). |
| **ADR registry** | Authoritative ADR status index: `specs/adr-registry.md`. |
| **Interface registry** | `specs/interfaces.md` — cross-module data contracts. |

---

## Reconciliation notes

- **Network vs shapes:** `netconvert` builds drivable networks; `polyconvert` builds ancillary geometry. Do not conflate.
- **OMX zones vs TAZ:** OMX matrix indices/names must align with TAZ ids or API must map them (ADR-014).
