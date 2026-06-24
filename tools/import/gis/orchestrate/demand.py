# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""VISUM OMX + SQLite demand build orchestration (ADR-005, ADR-006)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

from gis.normalize.demand_totals import ZoneDemandTotals, zone_demand_totals_by_core
from gis.normalize.visum_zones import (
    VisumZonesError,
    build_tazs_for_core,
    read_zone_connectors,
)
from gis.omx.adapter import (
    DEFAULT_CORES,
    DEFAULT_CORE_VTYPE,
    OmxAdapterOptions,
    write_taz_relation_for_core,
)
from gis.omx.validate import validate_demand_bearing_tazs, validate_zone_alignment
from gis.orchestrate.reachable_trips import ReachableTripsError, write_reachable_trips
from gis.orchestrate.subprocess_run import save_and_run

TripGeneration = Literal["reachable", "od2trips"]


@dataclass
class DemandBuildOptions:
    omx_options: OmxAdapterOptions = field(default_factory=OmxAdapterOptions)
    cores: tuple[str, ...] = DEFAULT_CORES
    core_vtype: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_CORE_VTYPE))
    run_od2trips: bool = True
    trip_generation: TripGeneration = "reachable"
    run_duarouter: bool = False


@dataclass
class DemandBuildResult:
    taz_relation_paths: dict[str, Path] = field(default_factory=dict)
    tazs_paths: dict[str, Path] = field(default_factory=dict)
    trips_paths: dict[str, Path] = field(default_factory=dict)
    routes_path: Optional[Path] = None
    relation_counts: dict[str, int] = field(default_factory=dict)
    excluded_zones: dict[str, list[str]] = field(default_factory=dict)
    skipped_cores: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    od2trips_returncodes: dict[str, int] = field(default_factory=dict)
    trip_counts: dict[str, int] = field(default_factory=dict)
    duarouter_returncode: Optional[int] = None


def demand_zones_by_core(
    omx_path: str | Path,
    cores: tuple[str, ...],
    *,
    mapping_name: str = "NO",
) -> dict[str, set[str]]:
    totals = zone_demand_totals_by_core(omx_path, cores, mapping_name=mapping_name)
    return {
        core: {zone_id for zone_id, t in zones.items() if t.has_external or t.intrazonal > 0}
        for core, zones in totals.items()
    }


def zero_demand_zones(
    omx_path: str | Path,
    cores: tuple[str, ...],
    *,
    mapping_name: str = "NO",
) -> set[str]:
    totals = zone_demand_totals_by_core(omx_path, cores, mapping_name=mapping_name)
    import openmatrix as omx

    with omx.open_file(str(omx_path), "r") as f:
        all_labels = {str(label) for label in f.mapping(mapping_name).keys()}
    active: set[str] = set()
    for zones in totals.values():
        for zone_id, t in zones.items():
            if t.has_external or t.intrazonal > 0:
                active.add(zone_id)
    return all_labels - active


def _external_demand_zones(totals: dict[str, ZoneDemandTotals]) -> set[str]:
    return {zone_id for zone_id, t in totals.items() if t.has_external}


def build_demand_from_visum(
    omx_path: str | Path,
    sqlite_path: str | Path,
    net_xml: str | Path,
    out_dir: str | Path,
    options: Optional[DemandBuildOptions] = None,
) -> DemandBuildResult:
    options = options or DemandBuildOptions()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    omx_path = Path(omx_path)
    sqlite_path = Path(sqlite_path)
    net_xml = Path(net_xml)
    net_local = out_dir / net_xml.name
    if net_xml.resolve() != net_local.resolve():
        shutil.copy2(net_xml, net_local)
    net_name = net_local.name

    result = DemandBuildResult()
    tables = read_zone_connectors(sqlite_path)
    totals_by_core = zone_demand_totals_by_core(
        omx_path,
        options.cores,
        mapping_name=options.omx_options.mapping_name,
    )
    zero_demand = zero_demand_zones(
        omx_path,
        options.cores,
        mapping_name=options.omx_options.mapping_name,
    )

    for core in options.cores:
        if core in options.omx_options.skip_cores:
            result.skipped_cores.append(core)
            continue
        vtype = options.core_vtype.get(core)
        if not vtype:
            result.messages.append(f"no vType for core {core!r}; skipped")
            continue

        core_totals = totals_by_core.get(core, {})

        tazs_path = out_dir / f"tazs.{vtype}.xml"
        taz_result = build_tazs_for_core(
            sqlite_path,
            net_xml,
            tazs_path,
            core=core,
            vtype=vtype,
            demand_totals=core_totals,
            zero_demand_zone_ids=zero_demand,
        )
        result.tazs_paths[vtype] = tazs_path
        result.excluded_zones[core] = taz_result.excluded_zones
        result.messages.extend(taz_result.messages)
        result.messages.extend(
            f"{core}: unmapped token {token} ({count} connectors)"
            for token, count in sorted(taz_result.unmapped_tokens.items())
        )

        taz_rel = out_dir / f"tazRelation.{vtype}.xml"
        omx_result = write_taz_relation_for_core(
            omx_path,
            taz_rel,
            core,
            options.omx_options,
            zone_access=taz_result.zone_access,
        )
        result.taz_relation_paths[vtype] = taz_rel
        result.relation_counts[core] = omx_result.relation_counts.get(core, 0)
        result.skipped_cores.extend(omx_result.skipped_cores)
        result.messages.extend(omx_result.messages)

        validate_zone_alignment(omx_result.zone_ids, tables.zone_ids, {r.taz_id for r in taz_result.records})
        external_zones = _external_demand_zones(core_totals) - set(taz_result.excluded_zones)
        validate_demand_bearing_tazs(external_zones, {record.taz_id for record in taz_result.records})

        if not options.run_od2trips:
            continue

        trips_path = out_dir / f"trips.{vtype}.xml"
        if options.trip_generation == "reachable":
            try:
                trip_result = write_reachable_trips(
                    net_local,
                    tazs_path,
                    taz_rel,
                    trips_path,
                    vtype=vtype,
                    prefix=vtype,
                )
            except ReachableTripsError as exc:
                raise VisumZonesError(str(exc)) from exc
            result.trip_counts[vtype] = trip_result.trip_count
            result.messages.extend(trip_result.messages)
        else:
            log_path = out_dir / f"od2trips.{vtype}.log"
            code = save_and_run(
                "od2trips",
                [
                    "-n", tazs_path.name,
                    "-z", taz_rel.name,
                    "--vtype", vtype,
                    "--prefix", vtype,
                    "-o", trips_path.name,
                ],
                out_dir / f"od2trips.{vtype}.cfg",
                out_dir,
                log_path,
            )
            result.od2trips_returncodes[vtype] = code
            if code != 0:
                raise VisumZonesError(
                    f"od2trips for {vtype} exited with code {code}; see {log_path}"
                )
        result.trips_paths[vtype] = trips_path

    if options.run_duarouter and result.trips_paths:
        routes_path = out_dir / "routes.xml"
        trip_list = ",".join(path.name for path in result.trips_paths.values())
        vtypes = Path(__file__).resolve().parent.parent / "data" / "default_vtypes.add.xml"
        duarouter_args = ["-n", net_name]
        if vtypes.is_file():
            shutil.copy2(vtypes, out_dir / vtypes.name)
            duarouter_args.extend(["--additional-files", vtypes.name])
        duarouter_args.extend(["--trip-files", trip_list, "-o", routes_path.name])
        code = save_and_run(
            "duarouter",
            duarouter_args,
            out_dir / "duarouter.cfg",
            out_dir,
            out_dir / "duarouter.log",
        )
        result.duarouter_returncode = code
        if code != 0:
            raise VisumZonesError(
                f"duarouter exited with code {code}; see {out_dir / 'duarouter.log'}"
            )
        result.routes_path = routes_path

    return result
