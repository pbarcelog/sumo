# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Route assignment orchestration (duarouter / duaIterate)."""

from __future__ import annotations

import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from gis.orchestrate.subprocess_run import resolve_tool_script, run_binary, run_python_tool, save_and_run


class AssignmentMethod(str, Enum):
    DUAROUTER = "duarouter"
    DUAITERATE = "duaIterate"


class AssignmentError(RuntimeError):
    pass


@dataclass
class AssignmentOptions:
    method: AssignmentMethod = AssignmentMethod.DUAITERATE
    iterations: int = 2
    begin: int = 0
    end: int = 7200
    vtypes_path: Optional[Path] = None


@dataclass
class AssignmentResult:
    routes_path: Path
    log_path: Path
    returncode: int
    method: AssignmentMethod
    messages: list[str] = field(default_factory=list)


def default_vtypes_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "default_vtypes.add.xml"


def ensure_vtypes(dest: Path, source: Optional[Path] = None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = source or default_vtypes_path()
    if not src.is_file():
        raise AssignmentError(f"vTypes file not found: {src}")
    shutil.copy2(src, dest)
    return dest


def _sumo_path(path: Path, base: Path) -> str:
    return os.path.relpath(path.resolve(), base.resolve()).replace("\\", "/")


def trip_files_arg_relative(trip_paths: dict[str, Path], base: Path) -> str:
    return ",".join(_sumo_path(path, base) for path in trip_paths.values())


def _vtypes_relative(vtypes: Path, cwd: Path) -> str:
    return _sumo_path(vtypes, cwd)


def _merge_route_files(sources: list[Path], dest: Path) -> None:
    root = ET.Element(
        "routes",
        {
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:noNamespaceSchemaLocation": "http://sumo.dlr.de/xsd/routes_file.xsd",
        },
    )
    seen_vtypes: set[str] = set()
    for source in sources:
        tree = ET.parse(source)
        for child in tree.getroot():
            if child.tag == "vType":
                vid = child.get("id")
                if vid in seen_vtypes:
                    continue
                seen_vtypes.add(vid)
                root.append(child)
            elif child.tag in ("vehicle", "flow"):
                root.append(child)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(dest, encoding="UTF-8", xml_declaration=True)


def _dua_iterate_output_routes(assignment_dir: Path, trip_paths: dict[str, Path], last_step: int) -> list[Path]:
    step_dir = assignment_dir / f"{last_step:03d}"
    if not step_dir.is_dir():
        raise AssignmentError(f"duaIterate output directory missing: {step_dir}")
    outputs: list[Path] = []
    for trip in trip_paths.values():
        stem = trip.stem
        candidate = step_dir / f"{stem}_{last_step:03d}.rou.xml"
        if not candidate.is_file():
            raise AssignmentError(f"duaIterate route output missing: {candidate}")
        outputs.append(candidate)
    return outputs


def run_assignment(
    *,
    net_xml: Path,
    trip_paths: dict[str, Path],
    assignment_dir: Path,
    vtypes_xml: Path,
    options: Optional[AssignmentOptions] = None,
) -> AssignmentResult:
    options = options or AssignmentOptions()
    assignment_dir.mkdir(parents=True, exist_ok=True)
    routes_path = assignment_dir / "routes.xml"
    log_path = assignment_dir / f"{options.method.value}.log"

    if not trip_paths:
        raise AssignmentError("no trip files to assign")

    trip_arg = trip_files_arg_relative(trip_paths, assignment_dir)
    vtypes_rel = _vtypes_relative(vtypes_xml, assignment_dir)

    if options.method == AssignmentMethod.DUAROUTER:
        net_rel = _sumo_path(net_xml, assignment_dir)
        code = save_and_run(
            "duarouter",
            [
                "-n", net_rel,
                "--additional-files", vtypes_rel,
                "--trip-files", trip_arg,
                "-o", routes_path.name,
                "--no-step-log",
            ],
            assignment_dir / "duarouter.cfg",
            assignment_dir,
            log_path,
        )
        if code != 0:
            raise AssignmentError(f"duarouter exited with code {code}; see {log_path}")
        return AssignmentResult(
            routes_path=routes_path,
            log_path=log_path,
            returncode=code,
            method=options.method,
        )

    script = resolve_tool_script("assign/duaIterate.py")
    if not Path(script).is_file():
        raise AssignmentError(
            f"duaIterate.py not found at {script}; set SUMO_HOME to the SUMO installation"
        )

    net_rel = _sumo_path(net_xml, assignment_dir)
    trip_rel = trip_files_arg_relative(trip_paths, assignment_dir)
    last_step = max(options.iterations, 1)
    dua_args = [
        "-n", net_rel,
        "-t", trip_rel,
        "-f", "0",
        "-l", str(last_step),
        "-b", str(options.begin),
        "-e", str(options.end),
        "--log", log_path.name,
        "--dualog", "duaIterate.dualog",
        f"duarouter--additional-files={vtypes_rel}",
    ]
    code = run_python_tool(script, dua_args, assignment_dir, log_path)
    if code != 0:
        raise AssignmentError(f"duaIterate exited with code {code}; see {log_path}")

    last_iter = last_step - 1
    route_parts = _dua_iterate_output_routes(assignment_dir, trip_paths, last_iter)
    _merge_route_files(route_parts, routes_path)
    return AssignmentResult(
        routes_path=routes_path,
        log_path=log_path,
        returncode=code,
        method=options.method,
        messages=[f"merged {len(route_parts)} route files from iteration {last_iter}"],
    )
