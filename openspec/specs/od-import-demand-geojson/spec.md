# od-import-demand-geojson

VISUM federated GeoJSON demand import: OMX + `zone_centroid.geojson` + `connector.geojson` →
`tazRelation.xml` + `tazs.xml` → trips (ADR-005, ADR-006, ADR-012, ADR-014).
Translation rules are normative in the archived change
`openspec/changes/archive/2026-06-26-import-od-demand-geojson/data-inventory.md`.

**PRD:** §1 (OMX + spatial → demand), §2 (formats), §4 (fail-loud, traceability)

## Requirements
### Requirement: Read zone identity from GeoJSON centroids

The importer SHALL read `zone_centroid.geojson` and derive the zone id set from each feature's `NO`
property. PRD §2.

#### Scenario: Zone centroids loaded

- **WHEN** valid `zone_centroid.geojson` is supplied
- **THEN** the importer produces one zone id per feature using `NO` as the TAZ id

### Requirement: Expand connector GeoJSON into directed connector rows

The importer SHALL read `connector.geojson` and expand each feature into AB and/or BA directed rows
using `ZONENO`/`NODENO`/`DIRECTION`/`TSYSSET` and the `R_*` fields, matching SQLite `CONNECTOR`
semantics. Team decision (proven 1:1 on Karlsruhe).

#### Scenario: AB and BA rows emitted

- **WHEN** a connector feature has `DIRECTION=O` and `R_DIRECTION=D` with non-empty `TSYSSET` and
  `R_TSYSSET`
- **THEN** two directed rows are produced equivalent to SQLite `CONNECTOR` rows

#### Scenario: Empty TSYSSET direction skipped

- **WHEN** a connector direction has an empty transport-system set
- **THEN** that direction is omitted and recorded in the build report

### Requirement: Align OMX zone labels with GeoJSON zone ids

The importer SHALL require OMX named-mapping labels to match `zone_centroid` `NO` values exactly.
ADR-012, ADR-014; fail loud on unknown zones. PRD §4.

#### Scenario: OMX and centroids align

- **WHEN** `Visum_3_modes.omx` mapping `NO` and `zone_centroid.geojson` are both supplied for Karlsruhe
- **THEN** both sets contain 726 ids with zero symmetric difference

### Requirement: Resolve connectors to tazSource and tazSink edges

The importer SHALL map expanded connector rows to `tazSource`/`tazSink` incident edges in the built
`net.xml` using the same rules as the SQLite `CONNECTOR` path (direction `O`/`D`, vClass filter,
uniform weights). ADR-014.

#### Scenario: CAR connector resolves to network edges

- **WHEN** zone `110` has a connector with `TSYSSET` containing `CAR` and `NODENO` present in `net.xml`
- **THEN** the zone's `tazs.xml` entry includes at least one `tazSource` or `tazSink` edge that allows
  `passenger`

### Requirement: Emit OMX tazRelation per core

The importer SHALL reuse the OMX adapter to emit `tazRelation.xml` intervals per non-empty core with zone
ids from the `NO` mapping. ADR-012.

#### Scenario: Car and HVG intervals produced

- **WHEN** the OMX contains `Car` and `HVG` cores with positive cells
- **THEN** `tazRelation.xml` contains intervals for those cores with `from`/`to` ids equal to zone `NO`
  values

### Requirement: Build demand artifacts via library entry point

The importer SHALL expose `build_demand_from_geojson(omx_path, zone_centroid_path, connector_path,
net_xml, out_dir, options)` returning a build report with artifact paths and per-core summaries.
ADR-009.

#### Scenario: Demand build produces tazs and tazRelation

- **WHEN** valid OMX, zone centroid, connector GeoJSON, and `net.xml` are supplied
- **THEN** the output directory contains per-core `tazs.xml` and `tazRelation.xml` files

### Requirement: Orchestrate trip generation

The importer SHALL invoke trip generation (`reachable` or `od2trips` per options) using
`sumolib.checkBinary`, saving configuration and logs. ADR-006.

#### Scenario: Non-empty trips for Car core

- **WHEN** Karlsruhe OMX + GeoJSON zones/connectors + GeoJSON `net.xml` are built with default options
- **THEN** passenger trips are produced with a non-zero trip count

### Requirement: Fail loud on unreadable input or unresolvable access

The importer SHALL raise explicit errors for unreadable GeoJSON, OMX/zone misalignment, and zones with
external demand but no resolvable connector edges. PRD §4.

#### Scenario: Malformed connector GeoJSON

- **WHEN** `connector.geojson` cannot be parsed
- **THEN** the import fails with an explicit error identifying the file

### Requirement: Do not use heuristic connector generation in v1

The importer SHALL NOT synthesize connectors from zone polygons or centroids alone when
`connector.geojson` is the declared source. Team decision (AequilibraE stage 1 only).

#### Scenario: No polygon inference

- **WHEN** `connector.geojson` is supplied
- **THEN** `tazs.xml` edge assignments derive only from expanded connector rows, not from
  `zone_polygon.geojson` geometry

### Requirement: Validate against real Karlsruhe federated export

The importer SHALL be verified against real Karlsruhe OMX + GeoJSON zone/connector files and a
GeoJSON-built `net.xml`, with `tazs.xml` parity to the SQLite path for Car/HVG. Team decision.

#### Scenario: Real-file smoke

- **WHEN** the real Karlsruhe federated files are imported
- **THEN** non-empty expanded connector rows match SQLite `CONNECTOR` on
  `(ZONENO,NODENO,DIRECTION,TSYSSET)`; OMX aligns with 726 zones; and Car/HVG `tazs.xml` match the
  SQLite-derived artifacts for the same `net.xml`

