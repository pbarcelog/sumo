# ADR-007: Data Contracts (XML/XSD)

**Status:** Accepted (documented from code)
**Tier:** A
**Sources:** `data/xsd/`, `data/typemap/`

## Context

SUMO tools exchange XML validated against XSD schemas. The API output artifacts must conform.

## Decision

**Key schemas for GIS API:**

| Schema | File | Used by |
|---|---|---|
| Network | `data/xsd/net_file.xsd` | netconvert output |
| Additional (shapes) | `data/xsd/additional_file.xsd` | polyconvert |
| TAZ | `data/xsd/taz_file.xsd` | taz definitions |
| Data modes (tazRelation) | `data/xsd/datamode_file.xsd` | OD matrices |
| Routes | `data/xsd/routes_file.xsd` | duarouter output |
| Trips | `data/xsd/routes_file.xsd` (trips subset) | od2trips output |

**Typemaps** (`data/typemap/`):

- `osmNetconvert.typ.xml`, `osmPolyconvert.typ.xml` — OSM feature mapping.
- API may need custom typemaps for non-OSM GIS attributes (team decision).

Validation tooling: [XML_Validation.md](../../docs/web/docs/Developer/XML_Validation.md).

## Consequences

- OMX adapter output must validate against `datamode_file.xsd`.
- API should optionally validate artifacts before returning to clients.

## References

- PRD §4
