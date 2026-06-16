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
| **TraCI** | Traffic Control Interface — runtime API to control a running simulation. Python client: `tools/traci/` (socket by default). Manual: `docs/web/docs/TraCI/index.md`. |
| **Libsumo** | In-process TraCI API (C++/SWIG); activated via `LIBSUMO_AS_TRACI=1` to replace socket `traci`. No `traci.connect` — use `traci.start` / `libsumo.start`. Manual: `docs/web/docs/Libsumo.md`. |
| **Libtraci** | C++ TraCI client API-compatible with libsumo; activated via `LIBTRACI_AS_TRACI=1`. Manual: `docs/web/docs/Libtraci.md`. |
| **sumolib** | Python library for SUMO file I/O and binary invocation (`tools/sumolib/`). |
| **checkBinary** | `sumolib.checkBinary(name, bindir)` — resolves a SUMO executable via `*_BINARY` env, `SUMO_HOME`, bindir, or wheel install (`tools/sumolib/__init__.py`). |
| **.sumocfg** | SUMO run configuration XML; produced by `sumo --save-configuration` (osmWebWizard pattern) or hand-authored; consumed by `sumo -c`. |
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
| **TextTest** | Acceptance-test framework used by upstream SUMO; compares stdout/stderr and collateral files to golden `*.tools` expectations. Manual: `docs/web/docs/Developer/Tests.md`. |
| **tools test suite** | TextTest application `tools` — config `tests/tools/config.tools`; includes `tests/tools/sumolib/`, `tests/tools/import/`, and (planned) `tests/tools/import/gis/`. |

---

## Reconciliation notes

- **Network vs shapes:** `netconvert` builds drivable networks; `polyconvert` builds ancillary geometry. Do not conflate.
- **OMX zones vs TAZ:** OMX matrix indices/names must align with TAZ ids or API must map them (ADR-014).
- **R2 (2026-06-15):** Tier A ADRs accepted; remaining gaps G-1–G-8 tracked in [reconciliation-r2.md](reconciliation-r2.md).
