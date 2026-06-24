# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""End-to-end VISUM scenario build: demand + assignment + manifest."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from gis.orchestrate.assignment import (
    AssignmentMethod,
    AssignmentOptions,
    AssignmentResult,
    ensure_vtypes,
    run_assignment,
)
from gis.orchestrate.demand import DemandBuildOptions, DemandBuildResult, build_demand_from_visum
from gis.workspace.manifest import (
    BuildManifest,
    RebuildPlan,
    build_manifest,
    load_manifest,
    plan_rebuild,
    save_manifest,
)
from gis.workspace.reference import ScenarioReferenceLayout


@dataclass
class RunnableScenarioOptions:
    scenario_id: str = "scenario"
    demand: DemandBuildOptions = field(default_factory=DemandBuildOptions)
    assignment: AssignmentOptions = field(default_factory=AssignmentOptions)
    emit_sumocfg: bool = True
    sumocfg_breakpoint: Optional[int] = 1800
    time_to_teleport: int = 300
    copy_sources: bool = False


@dataclass
class RunnableScenarioResult:
    layout: ScenarioReferenceLayout
    rebuild_plan: RebuildPlan
    demand: Optional[DemandBuildResult] = None
    assignment: Optional[AssignmentResult] = None
    manifest: Optional[BuildManifest] = None
    sumocfg_path: Optional[Path] = None
    messages: list[str] = field(default_factory=list)


def _copy_if_needed(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)


def _discover_trips(demand_dir: Path) -> dict[str, Path]:
    trips: dict[str, Path] = {}
    for path in sorted(demand_dir.glob("trips.*.xml")):
        vtype = path.stem.split(".", 1)[1]
        trips[vtype] = path
    return trips


def _write_sumocfg(
    layout: ScenarioReferenceLayout,
    scenario_id: str,
    *,
    begin: int,
    end: int,
    time_to_teleport: int,
    breakpoint: Optional[int],
) -> Path:
    cfg_path = layout.sim / f"{scenario_id}.sumocfg"
    breakpoint_line = (
        f'        <breakpoints value="{breakpoint}"/>\n' if breakpoint is not None else ""
    )
    cfg_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="../network/net.net.xml"/>
        <route-files value="../assignment/routes.xml"/>
        <additional-files value="vtypes.add.xml"/>
    </input>
    <time>
        <begin value="{begin}"/>
        <end value="{end}"/>
        <step-length value="1"/>
    </time>
    <processing>
        <time-to-teleport value="{time_to_teleport}"/>
        <max-depart-delay value="900"/>
    </processing>
    <report>
        <verbose value="true"/>
        <no-step-log value="true"/>
        <log value="sumo.log"/>
        <message-log value="sumo-messages.log"/>
    </report>
    <gui_only>
{breakpoint_line}    </gui_only>
</configuration>
""",
        encoding="utf-8",
    )
    return cfg_path


def build_runnable_scenario(
    omx_path: str | Path,
    sqlite_path: str | Path,
    net_xml: str | Path,
    workspace_root: str | Path,
    options: Optional[RunnableScenarioOptions] = None,
) -> RunnableScenarioResult:
    options = options or RunnableScenarioOptions()
    layout = ScenarioReferenceLayout.create(workspace_root)
    omx_path = Path(omx_path)
    sqlite_path = Path(sqlite_path)
    net_xml = Path(net_xml)

    existing = load_manifest(layout.manifest_path)
    trips_exist = bool(_discover_trips(layout.demand))
    routes_exist = layout.routes_xml.is_file()
    rebuild = plan_rebuild(
        existing,
        omx=omx_path,
        sqlite=sqlite_path,
        net_xml=net_xml,
        assignment_method=options.assignment.method.value,
        assignment_iterations=options.assignment.iterations,
        assignment_begin=options.assignment.begin,
        assignment_end=options.assignment.end,
        trips_exist=trips_exist,
        routes_exist=routes_exist,
    )

    result = RunnableScenarioResult(layout=layout, rebuild_plan=rebuild)

    if options.copy_sources:
        _copy_if_needed(omx_path, layout.sources / omx_path.name)
        _copy_if_needed(sqlite_path, layout.sources / sqlite_path.name)

    _copy_if_needed(net_xml, layout.net_xml)
    vtypes = ensure_vtypes(layout.vtypes_xml, options.assignment.vtypes_path)

    if rebuild == RebuildPlan.SKIP:
        result.messages.append("inputs unchanged; skipping demand and assignment")
        result.manifest = existing
        if options.emit_sumocfg:
            result.sumocfg_path = _write_sumocfg(
                layout,
                options.scenario_id,
                begin=options.assignment.begin,
                end=options.assignment.end,
                time_to_teleport=options.time_to_teleport,
                breakpoint=options.sumocfg_breakpoint,
            )
        return result

    demand_result: Optional[DemandBuildResult] = None
    trip_paths: dict[str, Path]

    if rebuild == RebuildPlan.FULL:
        demand_opts = replace(options.demand, run_duarouter=False)
        demand_result = build_demand_from_visum(
            omx_path,
            sqlite_path,
            layout.net_xml,
            layout.demand,
            demand_opts,
        )
        trip_paths = dict(demand_result.trips_paths)
        result.demand = demand_result
    else:
        trip_paths = _discover_trips(layout.demand)
        if not trip_paths:
            raise RuntimeError("assignment-only rebuild requested but demand/trips.* missing")
        result.messages.append("reusing existing demand/trips.*")

    assignment_result = run_assignment(
        net_xml=layout.net_xml,
        trip_paths=trip_paths,
        assignment_dir=layout.assignment,
        vtypes_xml=vtypes,
        options=options.assignment,
    )
    result.assignment = assignment_result

    artifacts = {
        "net_xml": str(layout.net_xml.relative_to(layout.root)),
        "routes_xml": str(layout.routes_xml.relative_to(layout.root)),
        "vtypes_xml": str(layout.vtypes_xml.relative_to(layout.root)),
    }
    for vtype, path in trip_paths.items():
        artifacts[f"trips_{vtype}"] = str(path.relative_to(layout.root))

    manifest = build_manifest(
        omx=omx_path,
        sqlite=sqlite_path,
        net_xml=layout.net_xml,
        assignment_method=options.assignment.method.value,
        assignment_iterations=options.assignment.iterations,
        assignment_begin=options.assignment.begin,
        assignment_end=options.assignment.end,
        artifacts=artifacts,
    )
    save_manifest(layout.manifest_path, manifest)
    result.manifest = manifest

    if options.emit_sumocfg:
        result.sumocfg_path = _write_sumocfg(
            layout,
            options.scenario_id,
            begin=options.assignment.begin,
            end=options.assignment.end,
            time_to_teleport=options.time_to_teleport,
            breakpoint=options.sumocfg_breakpoint,
        )

    return result
