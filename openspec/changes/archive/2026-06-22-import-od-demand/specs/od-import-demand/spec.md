# od-import-demand

VISUM OD demand import: OMX matrix + `ZONE`/`CONNECTOR` → `tazRelation.xml` + `tazs.xml` → `od2trips`
(ADR-005, ADR-006, ADR-012, ADR-014). Translation rules are normative in this change's
`data-inventory.md`; scenarios below cite **real cores, zone ids, and connector rows measured in the
Karlsruhe `Visum_3_modes.omx` and `Karlsruhe-sqlite.sqlite3`**.

**PRD:** §1 (OMX + spatial → demand), §2 (OMX format), §4 (fail-loud, traceability)

## ADDED Requirements

### Requirement: Read OMX zone labels from the named mapping

The adapter SHALL read OMX via Python `openmatrix` and derive `tazRelation` zone ids from the OMX
**named mapping** (here `NO`), not from positional matrix indices, so the emitted ids equal the VISUM
zone numbers. PRD §2 (OMX format); ADR-012; data-inventory §3–4.

#### Scenario: Mapping labels used as zone ids

- **WHEN** `Visum_3_modes.omx` is read (root `SHAPE [726 726]`, one mapping `NO` with labels
  `110 … 2,000,142`)
- **THEN** the `tazRelation` `from`/`to` ids are the mapping labels (e.g. `110`), and matrix row/column
  index `0` resolves to id `110` — never the literal index `0`

#### Scenario: Missing mapping is reported, not silently indexed

- **WHEN** an OMX file has no named mapping
- **THEN** the adapter reports the absence (warning or explicit error per build options) rather than
  silently emitting 0-based integer ids

### Requirement: Emit one tazRelation interval per non-empty core

The adapter SHALL emit one `tazRelation` `<interval>` per non-empty OMX core, identified by the core,
with relations for every cell whose value is greater than zero, validating against the
`datamode_file.xsd` (ADR-007). PRD §2 (OMX format); ADR-012; data-inventory §4.

#### Scenario: Three cores become three intervals

- **WHEN** the OMX has cores `Car` (Σ ≈ 776,785), `HVG` (Σ ≈ 51,155), and `PUT` (Σ ≈ 139,821)
- **THEN** the output contains a distinct interval per emitted core, each carrying `<tazRelation
  from=… to=… count=…/>` for its non-zero cells (e.g. `Car` has 229,604 non-zero relations)

#### Scenario: Zero cells skipped

- **WHEN** a core cell value is `0`
- **THEN** no `tazRelation` is written for that OD pair

### Requirement: Map OMX cores to vehicle types

The adapter SHALL map each OMX core to a SUMO vType via a configurable mapping consistent with
`import-network-sqlite` (`Car→passenger`, `HVG→truck`), report any unmapped core, and handle the `PUT`
core per the configured policy (default: skip with a report, since PuT demand has no road path).
PRD §2; team decision (mode map consistent with `import-network-sqlite`); data-inventory §6.

#### Scenario: Car and HVG map to road vTypes

- **WHEN** cores `Car` and `HVG` are converted
- **THEN** the `Car` interval uses vType `passenger` and the `HVG` interval uses vType `truck`

#### Scenario: PUT skipped by default with a report

- **WHEN** the `PUT` core is present and `skip_put` is enabled (default)
- **THEN** no road demand is emitted for `PUT` and the build report records that `PUT` was skipped

### Requirement: Preserve intrazonal demand when a spawn/absorb path exists

The adapter SHALL emit intrazonal (diagonal, `from == to`) cells by default when the zone has at least
one resolvable `tazSource` and `tazSink` for that mode, with an option to drop all intrazonal cells.
When intrazonal demand exists but the zone has no path, the adapter SHALL drop the diagonal cell with
a warning. Team decision (real intrazonal demand present, data-inventory §4, §5.4).

#### Scenario: Diagonal cells emitted when path exists

- **WHEN** the `Car` core has non-zero diagonal demand (Σ ≈ 1,585 across the diagonal) and the zone
  resolves at least one `tazSource` and one `tazSink`
- **THEN** `tazRelation` entries with `from == to` are written unless intrazonal demand is disabled

#### Scenario: Intrazonal-only zone without car path is dropped

- **WHEN** zone `3951` has intrazonal Car demand only and its CAR connectors resolve only to
  bicycle-allowed edges
- **THEN** the diagonal `tazRelation` for `3951` is omitted with a warning and the zone is excluded
  from the `passenger` `tazs.xml`

### Requirement: Resolve connector nodes to network edges for TAZ sources and sinks

The importer SHALL build `tazs.xml` from VISUM `ZONE` and `CONNECTOR` by mapping each
`CONNECTOR.NODENO` to the SUMO node id (`NODE.NO`, preserved by `import-network-sqlite`) and resolving
incident edges of the built `net.xml`: `DIRECTION='O'` connectors become `tazSource` on edges leaving
the node, `DIRECTION='D'` connectors become `tazSink` on edges entering the node. PRD §1 (spatial → demand);
ADR-014; data-inventory §5.3.

#### Scenario: Origin connector becomes a tazSource

- **WHEN** zone `110` has an `O` connector to `NODENO=105225992` with `TSYSSET` containing `CAR`, and
  the network has an edge whose `from` node is `105225992`
- **THEN** the `taz` `110` lists that edge as a `tazSource`

#### Scenario: Destination connector becomes a tazSink

- **WHEN** zone `110` has a `D` connector to `NODENO=105225992` and the network has an edge whose `to`
  node is `105225992`
- **THEN** the `taz` `110` lists that edge as a `tazSink`

#### Scenario: Edges restricted to the target vClass

- **WHEN** a connector node is shared with PuT-only edges that do not `allow` `passenger`
- **THEN** those edges are excluded from the `passenger` `taz` source/sink set

### Requirement: Assign uniform weights to TAZ edges (v1)

The importer SHALL assign **equal weight** to every deduplicated `tazSource`/`tazSink` edge for a zone
and direction. It SHALL **not** read VISUM `WEIGHT(PRT)` or `WEIGHT(PUT)` in v1. Provisional business
assumption: `specs/assumptions/demand-taz-weighting-v1.md`; data-inventory §5.3, §10-d.

#### Scenario: Multi-connector zone gets uniform edge weights

- **WHEN** zone `110` has three `O` CAR connectors at different nodes, each resolving to one or more
  out-edges
- **THEN** every distinct out-edge in the union appears in `tazSource` with the **same** weight (e.g.
  `1`), regardless of each connector's `WEIGHT(PRT)` value

#### Scenario: Zero-weight connector is not treated specially

- **WHEN** a CAR connector has `WEIGHT(PRT)=0` but resolves to at least one vClass-allowed edge
- **THEN** those edges are included in the `tazSource` or `tazSink` set with the same uniform weight as
  edges from other connectors (the weight field is ignored)

### Requirement: Enforce strict zone-id alignment across OMX, ZONE, and tazs

The importer SHALL require every OMX zone label to exist in `ZONE.NO` and in the emitted `tazs` id set,
and SHALL fail loud, naming the offending ids, when an OMX-referenced zone is unknown. ADR-014; PRD §4;
data-inventory §2, §5.4.

#### Scenario: Exact set match passes

- **WHEN** the OMX `NO` labels and `ZONE.NO` are compared (both 726 ids, range `110 … 2,000,142`)
- **THEN** alignment succeeds with no missing ids on either side

#### Scenario: Unknown OMX zone fails loud

- **WHEN** the OMX references a zone id absent from `ZONE.NO`
- **THEN** the build fails with an explicit error listing the unknown id, before `od2trips`

### Requirement: Fail loud when external demand lacks connector edge access

The importer SHALL fail loud, naming the zone and missing direction, when a zone has **external**
production but no resolvable `tazSource`, or **external** attraction but no resolvable `tazSink`, after
connector synthesis and vClass filtering. Intrazonal-only zones without a path are excluded and warned,
not errored. PRD §4; data-inventory §5.4.

#### Scenario: External demand zone missing a source edge

- **WHEN** a zone has non-zero external outgoing demand but none of its `O` connector nodes (including
  synthesized connectors) resolve to an edge leaving the node
- **THEN** the build fails with an explicit error naming the zone and the missing `tazSource`

#### Scenario: Synthesize missing connector direction from all opposite connectors

- **WHEN** a zone has `O` CAR connectors but no `D` CAR connectors at all and OMX external attraction
  requires inbound access
- **THEN** the importer synthesizes `D` connectors from every `O` connector (same node, same
  `TSYSSET`), logs a warning, and continues if at least one `tazSink` edge resolves

### Requirement: Report and exclude zero-demand public-transport-only zones

The importer SHALL report and exclude from the PrT `tazs.xml`, without error, zones that have no PrT
connector and zero demand in every emitted core. Team decision (data-inventory §2.4).

#### Scenario: External PuT-only zone excluded

- **WHEN** zones `2000115 … 2000142` have only `PUTW` connectors and zero demand in `Car`, `HVG`, and
  `PUT`
- **THEN** those 28 zones are excluded from the PrT `tazs.xml` and listed in the build report, and no
  error is raised

### Requirement: Report unmapped transport-system tokens

The importer SHALL report any `CONNECTOR.TSYSSET` token absent from the mode mapping, with the source
zone, without silently dropping the connector. PRD §4 (no silent drops); data-inventory §5.4 (AequilibraE pattern).

#### Scenario: Unmapped connector token reported

- **WHEN** a connector's `TSYSSET` contains a token not present in the mode mapping
- **THEN** the connector's mapped tokens are still used and the unmapped token is reported with its
  `ZONENO`

### Requirement: Orchestrate od2trips from the produced demand

The importer SHALL resolve `od2trips` through `sumolib.checkBinary` and invoke it with the built
`net.xml`, `tazs.xml`, and `tazRelation.xml` to produce `trips.xml`, optionally chaining `duarouter` to
produce `routes.xml`, saving the configuration and capturing logs. PRD §2 (scenario build); ADR-005,
ADR-006; data-inventory §8.

#### Scenario: od2trips produces trips

- **WHEN** `net.xml`, `tazs.xml`, and `tazRelation.xml` are passed to `od2trips`
- **THEN** a `trips.xml` is produced and the od2trips return code and log path are recorded in the
  build report

#### Scenario: Optional duarouter produces routes

- **WHEN** routing is requested
- **THEN** `duarouter` consumes `trips.xml` and `net.xml` to produce `routes.xml`

### Requirement: Emit demand artifacts deterministically

The importer SHALL produce `tazRelation.xml` and `tazs.xml` with a stable, deterministic ordering
(intervals by core, relations by `(from, to)`, and `tazSource`/`tazSink` edges by edge id) so identical
inputs yield byte-identical artifacts. PRD §4 (determinism).

#### Scenario: Repeated runs are byte-identical

- **WHEN** the same OMX, SQLite, and `net.xml` are processed twice
- **THEN** the produced `tazRelation.xml` and `tazs.xml` are byte-identical (relations and edges in a
  stable sorted order, multi-connector zones included)

### Requirement: Validate against the real Karlsruhe OMX and SQLite

The importer SHALL be verified against the real `Visum_3_modes.omx`, `Karlsruhe-sqlite.sqlite3`, and the
`net.xml` built by `import-network-sqlite`, producing aligned `tazRelation.xml` + `tazs.xml` and a
non-empty `trips.xml`. Team decision (data-first acceptance); data-inventory §12.

#### Scenario: Real-data smoke

- **WHEN** the real OMX, SQLite, and `net.xml` are processed end-to-end
- **THEN** the OMX `NO` set equals `ZONE.NO` (726 ids), every demand-bearing zone resolves at least one
  `tazSource` and one `tazSink`, the 28 PuT-only zones are excluded, and `od2trips` emits a non-empty
  `trips.xml`
