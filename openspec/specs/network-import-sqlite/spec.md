# network-import-sqlite

VISUM SQLite network import to SUMO `net.xml` (ADR-006, ADR-011, ADR-013).
Translation rules are normative in the change's `data-inventory.md`; scenarios below cite **real
fields measured in the Karlsruhe DB**.

**PRD:** §2 (formats), §4 (quality/CRS)

## ADDED Requirements

### Requirement: Discover and validate VISUM SQLite tables

The importer SHALL open the SQLite database, require the tables `NETWORK`, `NODE`, `LINK`, `LINKTYPE`,
and `TSYS`, treat `LINKPOLY` as optional geometry, and report public-transport, turn, fare, and zone
tables as recognized-but-deferred without importing them. PRD §2, ADR-013.

#### Scenario: Required tables present

- **WHEN** a SQLite export containing `NETWORK`, `NODE`, `LINK`, `LINKTYPE`, and `TSYS` is supplied
- **THEN** discovery succeeds and the deferred tables (e.g. `STOP`, `LINE`, `LINEROUTE`, `TURN`) are
  listed in the build report as deferred, not imported

#### Scenario: Missing required table

- **WHEN** the database lacks a required table (e.g. `LINKTYPE`)
- **THEN** the import fails with an explicit error naming the missing table, before any build

### Requirement: Preserve VISUM identifiers

The importer SHALL use VISUM `NODE.NO` as the SUMO node id and `LINK.NO` as the (signed) SUMO edge id,
without renumbering. Team decision (round-trip traceability to source).

#### Scenario: Identifiers preserved

- **WHEN** a link `NO=3118` connects `FROMNODENO=100201` and `TONODENO=100202`
- **THEN** the SUMO nodes are `100201` and `100202` and the edge id derives from `3118` (signed per the
  direction rule)

### Requirement: Pair directed link rows into AB and reverse edges

The importer SHALL group `LINK` rows by `NO` (each direction is its own row sharing `NO` with swapped
`FROMNODENO`/`TONODENO`), assign the AB edge id `NO` to the row ordered first by
`(FROMNODENO, TONODENO)` and the reverse edge id `-NO` to the swapped row, and SHALL create an edge for
a direction only when that row's `TSYSSET` is non-empty, logging every skipped direction. Team decision
(data-inventory §6; `USERDIRECTION` carries no orientation in this export).

#### Scenario: Bidirectional link yields two edges

- **WHEN** both rows of `NO=3118` have non-empty `TSYSSET`
- **THEN** edges `3118` (100201→100202) and `-3118` (100202→100201) are created

#### Scenario: One-way link skips the empty direction

- **WHEN** one row of a link `NO` has a non-empty `TSYSSET` and its paired row has empty `TSYSSET`
- **THEN** only the populated direction becomes an edge and the empty direction is recorded as skipped
  in the build report

#### Scenario: Fully closed link skipped

- **WHEN** both rows of a link `NO` have empty `TSYSSET`
- **THEN** no edge is created for that `NO` and the skip is logged

### Requirement: Translate TSYSSET to vClass permissions

The importer SHALL map each `TSYSSET` token to a SUMO `vClass` per `data-inventory.md` §4 using a
configurable `build_options.mode_mapping`, set the edge `allow` to the mapped set, and SHALL report any
unmapped TSys token (warning, with source `NO`) without dropping the edge. Team decision (from data
inspection; AequilibraE pattern; consistent with `import-network-geojson`).

#### Scenario: Mixed-mode link allows cars

- **WHEN** a link direction has `TSYSSET="BIKE,CAR,HGV"`
- **THEN** the edge `allow` includes `passenger`, `bicycle`, and `truck`

#### Scenario: Unmapped transport system reported

- **WHEN** a link direction's `TSYSSET` contains a token absent from the mode mapping
- **THEN** the edge is still created from its mapped tokens and the unmapped token is reported with the
  source `NO`

### Requirement: Import public-transport-only links without private access

The importer SHALL keep links whose `TSYSSET` excludes private classes (e.g. `V0PRT=0` PuT links) and
model them as edges permitting only their mapped PuT vClasses, never dropping them and never using an
epsilon speed to deter routing. Team decision (PuT infrastructure must exist for later OD/PT phases).

#### Scenario: PuT-only link excludes passenger

- **WHEN** a link direction has `TSYSSET="BUS,TRAIN,TRAM"`, `V0PRT=0`, and `TYPENO=8`
- **THEN** the edge `allow` is `bus rail_urban tram`, `passenger` is not permitted, and the edge speed
  is a positive value sourced from `LINKTYPE` (not zero, not epsilon)

### Requirement: Resolve edge speed from per-mode LINKTYPE speeds

The importer SHALL set the edge `speed` ceiling to the maximum of the speeds permitted for the edge's
allowed TSys tokens — `VMAX_PRTSYS(*)` for private modes and `VDEF_PUTSYS(*)` for public modes from the
joined `LINKTYPE` row, plus `LINK.V0PRT` when greater than zero — converted from km/h to m/s, and SHALL
record the source `NO`, `TYPENO`, and chosen ceiling. The resolved speed MUST be positive for every
edge. PRD §4 (data-inventory §5).

#### Scenario: Car link uses link-type max speed

- **WHEN** a link direction has `TSYSSET="BIKE,CAR,HGV"` and `V0PRT=30` on a `LINKTYPE` whose
  `VMAX_PRTSYS(CAR)=30`
- **THEN** the edge speed is `30 km/h` expressed in m/s (`8.33`)

#### Scenario: PuT-only link gets positive speed without fallback

- **WHEN** a link direction has `V0PRT=0` and `TYPENO=8` (`VDEF_PUTSYS(TRAM)=50`)
- **THEN** the edge speed is `50 km/h` in m/s, taken from `LINKTYPE`, with no `LC` fallback table and no
  epsilon

### Requirement: Model differing per-mode speeds as restrictions, not lane splits

The importer SHALL keep the edge `speed` ceiling at the fastest allowed mode and, for every allowed
`vClass` whose `LINKTYPE` per-mode speed is below that ceiling, express the lower speed via the edge
`type` with `<restriction vClass="..." speed="..."/>`, and SHALL NOT split a link into separate lanes to
represent per-mode speed. Team decision (data-inventory §5; lane data shows no dedicated per-mode lanes).

#### Scenario: Each slower allowed mode gets a restriction

- **WHEN** an edge allows `passenger`, `truck`, and `bus` on a link type with car 50, HGV 30, and bus
  45 km/h
- **THEN** the edge ceiling equals the car speed (50 km/h in m/s) and `<restriction>` entries carry
  `vClass="truck"` at 30 km/h and `vClass="bus"` at 45 km/h

#### Scenario: Mode at the ceiling gets no restriction

- **WHEN** an allowed mode's `LINKTYPE` speed equals the edge ceiling
- **THEN** no `<restriction>` is emitted for that mode

### Requirement: Log low speed incoherent with allowed modes

The importer SHALL keep low real speeds without flooring, and SHALL emit a coherence warning — without
dropping the edge — when the resolved speed ceiling is at or below a configurable low-speed threshold
(default 5 km/h) on an edge whose `allow` includes a motorized class (any class other than `bicycle`
and `pedestrian`). Team decision (data-inventory §5 step 7).

#### Scenario: Low ceiling on a motorized edge is flagged

- **WHEN** an edge allows `passenger` and resolves to a ceiling of `5 km/h` or less
- **THEN** the edge is still built at that speed and a coherence warning is logged with the source `NO`,
  `TYPENO`, and allowed modes

#### Scenario: Low ceiling on a bike/pedestrian edge is not flagged

- **WHEN** an edge allows only `bicycle` and/or `pedestrian` and resolves to a low ceiling
- **THEN** the edge is built at that speed and no coherence warning is emitted

### Requirement: Map lane count and defer per-lane permissions

The importer SHALL set SUMO `numLanes` from `LINK.NUMLANES`, SHALL NOT emit per-lane `allow`
permissions in v1, and SHALL NOT ingest `LANE.WIDTH` (using SUMO's default lane width). Team decision
(data-inventory §8: zero directed links have lanes with differing `TSYSSET`, so no dedicated-PT-lane
modelling is supported by this export; `LANE.WIDTH` is physical width unrelated to mode permissions).

#### Scenario: Lane count carried through

- **WHEN** a link direction has `NUMLANES=2`
- **THEN** the edge is built with `numLanes=2` and a single edge-level `allow` (no per-lane permissions)

### Requirement: Reconstruct link geometry from nodes and LINKPOLY

The importer SHALL build each edge shape from the source node coordinate, the ordered `LINKPOLY`
vertices for that directed link (reversed for the BA direction when only the forward polyline exists),
and the target node coordinate. Team decision (AequilibraE geometry pattern).

#### Scenario: Intermediate vertices preserved

- **WHEN** a directed link has `LINKPOLY` rows
- **THEN** the edge shape includes those vertices in `INDEX` order between the from-node and to-node

### Requirement: Reproject projected source coordinates to a metric CRS

The importer SHALL read the source CRS from `NETWORK.PROJECTIONDEFINITION`, reproject `NODE` and
`LINKPOLY` coordinates with pyproj to the target network CRS (default EPSG:25832, overridable via
`build_options.crs`), and SHALL record the resolved source WKT and target EPSG. No silent reprojection.
PRD §4, ADR-011.

#### Scenario: Sphere-Mercator reprojected and logged

- **WHEN** `NETWORK.PROJECTIONDEFINITION` describes a sphere `Mercator` projection and no override is
  given
- **THEN** coordinates are reprojected to EPSG:25832 and the build report records the source WKT and the
  target EPSG

#### Scenario: Missing source CRS fails loud

- **WHEN** `NETWORK.PROJECTIONDEFINITION` is absent and no `build_options.crs` override is supplied
- **THEN** the import fails with an explicit CRS error and no network is built

### Requirement: Build net.xml via netconvert

The importer SHALL resolve `netconvert` through `sumolib.checkBinary`, build from plain-XML node/edge
(and type) inputs in already-projected cartesian coordinates without further netconvert reprojection,
save the netconvert configuration, and emit `net.xml`. PRD §2 (artifact delivery), ADR-006.

#### Scenario: Network produced

- **WHEN** normalized nodes and edges are written to plain XML
- **THEN** netconvert produces `net.xml` and a saved `.netccfg` in the output directory

### Requirement: Synthesize signal control as a stand-in

The importer SHALL request `netconvert` traffic-light guessing for v1 and SHALL NOT consume
`NODE.CONTROLTYPE` or `SIGNALCONTROL` for real signal timings (deferred). Team decision (no
control-plan import yet).

#### Scenario: Guessed signals

- **WHEN** the network is built
- **THEN** traffic lights are produced by netconvert guessing and `CONTROLTYPE` is not used for timing

### Requirement: Fail loud on unreadable input

The importer SHALL raise an explicit error, without silent drops, when the database cannot be opened or
read as a VISUM SQLite export. PRD §4.

#### Scenario: Unreadable database

- **WHEN** the supplied path is not a readable SQLite database
- **THEN** the import fails with an explicit error identifying the file and reason

### Requirement: Validate against the real Karlsruhe export

The importer SHALL be verified against the real `Karlsruhe-sqlite.sqlite3`, producing a `net.xml` with
no zero-speed edges, with PuT-only edges disallowing `passenger`, and loadable by SUMO. Team decision
(data-first acceptance).

#### Scenario: Real-DB smoke

- **WHEN** the real Karlsruhe SQLite database is imported
- **THEN** node and edge counts fall within the documented ranges (≈ 8,432 nodes; 843 links fully
  skipped), no edge has zero speed, sampled PuT-only edges (e.g. `NO=3118`) disallow `passenger`, and
  `netconvert`/`sumo` load the produced `net.xml` without error
