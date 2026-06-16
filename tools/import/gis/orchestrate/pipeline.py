# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

import logging
import sys
from pathlib import Path

from gis.normalize import BuildOptions, normalize_inputs
from gis.omx import validate_zone_ids, write_taz_relation
from gis.orchestrate.subprocess_run import (
    resolve_tool_script,
    run_binary,
    run_python_tool,
    save_and_run,
)
from gis.workspace import BuildState, RunState, RunStatus, ScenarioPaths, ScenarioStatus, StatusStore

logger = logging.getLogger(__name__)


def _fail(store: StatusStore, step: str, message: str) -> None:
    store.set_build(
        ScenarioStatus(
            state=BuildState.FAILED,
            step=step,
            error={"code": "build_failed", "message": message, "details": None},
        )
    )
    raise RuntimeError(message)


def build_scenario(scenario_id: str, options: BuildOptions) -> None:
    paths = ScenarioPaths.create(scenario_id)
    store = StatusStore(paths.status_file)
    store.set_build(ScenarioStatus(state=BuildState.BUILDING, step="normalize", progress=0.1))

    try:
        normalized = normalize_inputs(paths.inputs, paths.build, options)
        store.set_build(ScenarioStatus(state=BuildState.BUILDING, step="netconvert", progress=0.3))

        if normalized.roads_path is None:
            _fail(store, "normalize", "No road network geometry found in uploads")

        net_path = paths.build / "net.net.xml"
        net_cfg = paths.build / "net.netccfg"
        prefix = normalized.roads_path.with_suffix("").name
        code = save_and_run(
            "netconvert",
            [
                "--shapefile-prefix",
                prefix,
                "--shapefile.geo",
                "--output-file",
                "net.net.xml",
            ],
            net_cfg,
            paths.build,
            paths.logs / "netconvert.log",
        )
        if code != 0:
            _fail(store, "netconvert", f"netconvert exited with code {code}")

        if normalized.zones_path:
            store.set_build(
                ScenarioStatus(state=BuildState.BUILDING, step="polyconvert", progress=0.45)
            )
            poly_cfg = paths.build / "build.polycfg"
            code = save_and_run(
                "polyconvert",
                [
                    "-n",
                    "net.net.xml",
                    "--shape-file",
                    str(normalized.zones_path.name),
                    "--shapefile.guess-projection",
                    "-o",
                    "zones.poly.xml",
                ],
                poly_cfg,
                paths.build,
                paths.logs / "polyconvert.log",
            )
            if code != 0:
                _fail(store, "polyconvert", f"polyconvert exited with code {code}")

            store.set_build(
                ScenarioStatus(state=BuildState.BUILDING, step="tazs", progress=0.55)
            )
            tazs_path = paths.build / "tazs.xml"
            edges_script = resolve_tool_script("edgesInDistricts.py")
            code = run_python_tool(
                edges_script,
                [
                    "-n",
                    "net.net.xml",
                    "-t",
                    str(normalized.zones_path),
                    "-o",
                    "tazs.xml",
                ],
                paths.build,
                paths.logs / "edgesInDistricts.log",
            )
            if code != 0:
                _fail(store, "tazs", f"edgesInDistricts exited with code {code}")

        omx_files = list(paths.inputs.glob("*.omx"))
        if omx_files:
            store.set_build(
                ScenarioStatus(state=BuildState.BUILDING, step="omx", progress=0.65)
            )
            taz_rel = paths.build / "tazRelation.xml"
            omx_zones = write_taz_relation(omx_files[0], taz_rel, options.vType)
            validate_zone_ids(omx_zones, normalized.zone_ids)

            store.set_build(
                ScenarioStatus(state=BuildState.BUILDING, step="od2trips", progress=0.75)
            )
            code = run_binary(
                "od2trips",
                [
                    "-n",
                    "net.net.xml",
                    "--taz-files",
                    "tazs.xml",
                    "-z",
                    "tazRelation.xml",
                    "-o",
                    "trips.xml",
                ],
                paths.build,
                paths.logs / "od2trips.log",
            )
            if code != 0:
                _fail(store, "od2trips", f"od2trips exited with code {code}")

            store.set_build(
                ScenarioStatus(state=BuildState.BUILDING, step="duarouter", progress=0.85)
            )
            code = run_binary(
                "duarouter",
                ["-n", "net.net.xml", "-t", "trips.xml", "-o", "routes.xml"],
                paths.build,
                paths.logs / "duarouter.log",
            )
            if code != 0:
                _fail(store, "duarouter", f"duarouter exited with code {code}")

        store.set_build(ScenarioStatus(state=BuildState.READY, step="done", progress=1.0))
    except Exception as exc:
        logger.exception("build failed scenario_id=%s", scenario_id)
        if store.get_build().state != BuildState.FAILED:
            _fail(store, store.get_build().step or "build", str(exc))
        raise


def run_simulation(scenario_id: str, run_id: str) -> None:
    paths = ScenarioPaths.create(scenario_id)
    store = StatusStore(paths.status_file)
    build = store.get_build()
    if build.state != BuildState.READY:
        raise RuntimeError(f"Scenario not ready for simulation: {build.state.value}")

    run_dir = paths.run_dir(run_id)
    store.set_run(RunStatus(run_id=run_id, state=RunState.RUNNING, step="sumo"))

    sumocfg = run_dir / "scenario.sumocfg"
    net = paths.build / "net.net.xml"
    routes = paths.build / "routes.xml"
    tripinfo = run_dir / "tripinfos.xml"
    summary = run_dir / "summary.xml"

    cfg_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<configuration>",
        f'    <input><net-file value="../build/{net.name}"/>',
    ]
    if routes.exists():
        cfg_lines.append(f'    <route-files value="../build/{routes.name}"/>')
    cfg_lines.extend(
        [
            "    </input>",
            "    <output>",
            f'        <tripinfo-output value="{tripinfo.name}"/>',
            f'        <summary-output value="{summary.name}"/>',
            "    </output>",
            "</configuration>",
        ]
    )
    sumocfg.write_text("\n".join(cfg_lines), encoding="utf-8")

    code = run_binary(
        "sumo",
        ["-c", sumocfg.name],
        run_dir,
        paths.logs / f"sumo_{run_id}.log",
    )
    artifacts = [str(p.relative_to(paths.root)) for p in (tripinfo, summary) if p.exists()]
    if code != 0:
        store.set_run(
            RunStatus(
                run_id=run_id,
                state=RunState.FAILED,
                step="sumo",
                error={"code": "simulation_failed", "message": f"sumo exit {code}", "details": None},
                artifacts=artifacts,
            )
        )
        raise RuntimeError(f"sumo exited with code {code}")

    store.set_run(
        RunStatus(
            run_id=run_id,
            state=RunState.COMPLETED,
            step="done",
            artifacts=artifacts,
        )
    )
