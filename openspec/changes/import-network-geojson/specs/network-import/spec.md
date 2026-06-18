# network-import

VISUM GeoJSON network import to SUMO `net.xml` (ADR-006, ADR-011).
Translation rules are normative in the change's `data-inventory.md`.

**PRD:** §2 (formats), §4 (quality/CRS)

## ADDED Requirements

### Requirement: Read VISUM GeoJSON node and link layers

The importer SHALL read a VISUM `node` GeoJSON (point geometry) and `link` GeoJSON (line geometry)
and normalize their flat `properties` into node and edge records. PRD §2.

#### Scenario: Node and link files read

- **WHEN** valid `node.geojson` and `link.geojson` are supplied
- **THEN** the importer produces one node record per `node` feature and one or two edge records per
  `link` feature

### Requirement: Preserve VISUM identifiers

The importer SHALL use VISUM `NO` as the SUMO node id, the AB edge id, and `-NO` as the reverse edge
id, without renumbering. Team decision (round-trip traceability to source).

#### Scenario: Identifiers preserved

- **WHEN** a link has `NO=3118`, `FROMNODENO=100201`, `TONODENO=100202`, and both directions present
- **THEN** edges `3118` (100201→100202) and `-3118` (100202→100201) are created with SUMO nodes
  `100201` and `100202`

### Requirement: Translate TSYSSET to vClass permissions

The importer SHALL map each `TSYSSET` token to a SUMO `vClass` per `data-inventory.md` §4 and set the
edge `allow` attribute to that set, so unlisted classes are disallowed. Team decision (from data
inspection).

#### Scenario: Mixed-mode link allows cars

- **WHEN** a link has `TSYSSET="BIKE,CAR,HGV"`
- **THEN** the edge `allow` includes `passenger`, `bicycle`, and `truck`

### Requirement: Import public-transport-only links without private access

The importer SHALL keep links whose `TSYSSET` excludes private classes (e.g. `V0PRT=0km/h`
PuT links) and model them as edges that permit only their mapped PuT vClasses, never dropping them
and never using an epsilon speed to deter routing. Team decision (PuT infrastructure must exist for
later OD/GTFS phases).

#### Scenario: PuT-only link excludes passenger

- **WHEN** a link has `TSYSSET="BUS,TRAIN,TRAM"` and `V0PRT="0km/h"`
- **THEN** the edge `allow` is `bus rail tram`, `passenger` is not permitted, and the edge speed is a
  positive fallback value (not zero, not epsilon)

### Requirement: Directional split from R_ fields

The importer SHALL create an AB edge when `TSYSSET` is non-empty and a reverse edge when
`R_TSYSSET` is non-empty, using the `R_*` attributes for the reverse direction, and SHALL skip (and
log) a direction whose transport-system set is empty. Team decision.

#### Scenario: One-way link

- **WHEN** a link has non-empty `TSYSSET` and empty `R_TSYSSET`
- **THEN** only the AB edge is created and the omitted reverse direction is recorded in the build
  report

### Requirement: Speed conversion with documented fallback

The importer SHALL convert `V0PRT` from km/h to m/s for the edge speed when greater than zero, and
otherwise apply the `LC`-based fallback speed defined in `data-inventory.md` §5, recording every
substitution. PRD §4.

#### Scenario: Zero private speed gets fallback

- **WHEN** a link has `V0PRT="0km/h"` and `LC="PuT"`
- **THEN** the edge speed is the configured `PuT` fallback (m/s) and the substitution is logged with
  the source link `NO`

### Requirement: Project geometry to UTM with logging

The importer SHALL treat input geometry as WGS84 (EPSG:4326) and invoke `netconvert` with auto-UTM
projection, and SHALL record the resolved target EPSG in the build report. No silent reprojection.
PRD §4.

#### Scenario: CRS resolved and logged

- **WHEN** the network is built from WGS84 input
- **THEN** the build report records the resolved projected EPSG (e.g. `25832`) used by netconvert

### Requirement: Build net.xml via netconvert

The importer SHALL resolve `netconvert` through `sumolib.checkBinary`, build from plain XML
node/edge inputs, save the netconvert configuration, and emit `net.xml`. ADR-006.

#### Scenario: Network produced

- **WHEN** normalized nodes and edges are written to plain XML
- **THEN** netconvert produces `net.xml` and a saved `.netccfg` in the output directory

### Requirement: Synthesize signal control as a stand-in

The importer SHALL request `netconvert` traffic-light guessing for v1 and SHALL NOT consume node
`CONTROLTYPE` for real signal timings (deferred). Team decision (no real signal data yet).

#### Scenario: Guessed signals

- **WHEN** the network is built
- **THEN** traffic lights are produced by netconvert guessing and `CONTROLTYPE` is not used for
  timing

### Requirement: Fail loud on unreadable or unprojectable input

The importer SHALL raise an explicit error, without silent drops, when a GeoJSON file cannot be read
or the geometry CRS cannot be established. PRD §4.

#### Scenario: Unreadable link file

- **WHEN** the link GeoJSON cannot be parsed
- **THEN** the import fails with an explicit error identifying the file and reason

### Requirement: Validate against the real Karlsruhe export

The importer SHALL be verified against the real `node.geojson` and `link.geojson`, producing a
`net.xml` with no zero-speed edges, with PuT-only edges disallowing `passenger`, and loadable by
SUMO. Team decision (data-first acceptance).

#### Scenario: Real-file smoke

- **WHEN** the real Karlsruhe node and link files are imported
- **THEN** node and edge counts fall within the documented ranges, no edge has zero speed, and
  `netconvert`/`sumo` load the produced `net.xml` without error
