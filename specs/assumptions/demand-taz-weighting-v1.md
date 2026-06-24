# Business assumption: TAZ edge weighting (v1)

**Status:** Provisional — modeller review recommended before calibration phase
**Scope:** `import-od-demand` v1; Karlsruhe VISUM SQLite + OMX path
**Supersedes:** data-inventory §10(d) weight-mapping proposals (2026-06-18 discussion)
**Related ADRs:** ADR-005 (demand pipeline), ADR-014 (TAZ derivation)

## Decision (v1)

**Ignore VISUM connector weights in the first implementation stage.**

When building `tazs.xml` from `CONNECTOR` rows:

1. Resolve qualifying connectors to incident network edges (O → `tazSource`, D → `tazSink`) per
   `data-inventory.md` §5.3 steps 1–2 and vClass filter (§10-e).
2. **Union** edges contributed by all qualifying connectors for that zone and direction; deduplicate by
   edge id.
3. Assign **equal weight** to every listed edge (`weight="1"` or equivalent). Do **not** read
   `WEIGHT(PRT)` or `WEIGHT(PUT)`.
4. Trip generation uses **`reachable_trips`** (fork default): for each OMX O–D cell, sample
   `(tazSource, tazSink)` only from edge pairs with a shortest path for the vType. Legacy
   `od2trips` remains available via `DemandBuildOptions.trip_generation="od2trips"`.
   `duarouter` routes using the explicit `from`/`to` edges on each trip.

## Rationale

- VISUM `WEIGHT(PRT)` is per connector (zone↔node), not per edge; mapping it to SUMO edge weights
  requires several non-obvious rules (within-node split, zero-weight connectors, sums ≠ 100, dead
  connectors, renormalization).
- Uniform selection is valid SUMO behaviour and unblocks agile delivery.
- Karlsruhe median ~2 CAR connectors per zone — uniform bias is likely acceptable for an initial
  microsim smoke run; revisit if calibration shows access-pattern errors.

## Deferred (future change)

- Honour `WEIGHT(PRT)` / `WEIGHT(PUT)` as relative probabilities across connectors, with documented
  within-node edge split policy.
- Optional weighting by edge capacity or connector travel time (`T0_TSYS*`).
- Flag in `DemandBuildOptions` (e.g. `connector_weighting: uniform | visum_prt`) when implemented.

## Review trigger

Revisit this assumption when:

- Modeller or calibration feedback indicates systematic bias at multi-connector zones (e.g. zone 110,
  319).
- A study requires fidelity to VISUM assignment connector splits.
