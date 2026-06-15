# ADR-001: SUMO Module Map

**Status:** Draft (documented from code)
**Tier:** A
**Sources:** `docs/web/docs/Developer/Implementation_Notes/Sumo_Modules.md`, `src/` layout

## Context

Agents navigating SUMO need a module map. The upstream implementation notes document core C++ modules and their purposes.

## Decision

Document the as-built module graph for GIS API-relevant areas:

| Module | Purpose | GIS API relevance |
|---|---|---|
| `netimport` | Read external network formats | Network from shapefile/OSM |
| `netbuild` | Build/prepare SUMO networks | Post-import topology |
| `netload` | Load network for simulation | Runtime graph |
| `polyconvert` | Import shapes/POIs | GeoJSON, shapefile, GPKG (unverified) |
| `router` | Base routing classes | duarouter/marouter |
| `od` | OD matrix handling | tazRelation, VISUM formats |
| `utils` | Shared utilities (options, xml, geom) | All binaries |
| `traci-server` | TraCI API server | Optional remote control |
| `microsim` | Simulation core | sumo runtime |
| `foreign` | Third-party libs (tcpip, rtree, etc.) | Infrastructure |

Full table: [Sumo_Modules.md](../../docs/web/docs/Developer/Implementation_Notes/Sumo_Modules.md).

Structure exploration: [ExploringTheStructure.md](../../docs/web/docs/Developer/ExploringTheStructure.md) (Doxygen nightly).

## Consequences

- Slice schedule follows dependency order: utils → netimport → polyconvert → od → tools.
- Defer `microsim`, `netedit`, `gui` unless API scope expands.

## References

- PRD §5
