# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Route assignment orchestration (duarouter / duaIterate)."""

from __future__ import annotations

import gzip
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


def _parse_routes_file(source: Path) -> ET.ElementTree:
    if source.name.endswith(".gz"):
        with gzip.open(source, "rb") as fh:
            return ET.parse(fh)
    return ET.parse(source)


def _vtypes_by_id(vtypes_xml: Path) -> dict[str, ET.Element]:
    by_id: dict[str, ET.Element] = {}
    for el in ET.parse(vtypes_xml).getroot():
        if el.tag == "vType":
            vid = el.get("id")
            if vid:
                by_id[vid] = el
    return by_id


def _stage_trips_for_dua_iterate(
    trip_paths: dict[str, Path],
    vtypes_xml: Path,
    staging_dir: Path,
) -> dict[str, Path]:
    """Embed vType definitions in trip inputs for duaIterate step 0.

    duaIterate forwards ``duarouter--*`` options to every duarouter call. Passing
    ``--additional-files`` with vTypes would duplicate definitions on iteration 1+
    when route files from the previous step already embed the same vType ids.
    """
    vtypes = _vtypes_by_id(vtypes_xml)
    staging_dir.mkdir(parents=True, exist_ok=True)
    staged: dict[str, Path] = {}
    for vtype_id, trip_path in trip_paths.items():
        vtype_el = vtypes.get(vtype_id)
        if vtype_el is None:
            raise AssignmentError(f"vType {vtype_id!r} not found in {vtypes_xml}")
        dest = staging_dir / f"{trip_path.stem}.dua.xml"
        vtype_xml = ET.tostring(vtype_el, encoding="unicode").strip()
        with dest.open("w", encoding="utf-8", newline="\n") as out:
            out.write('<?xml version="1.0" encoding="UTF-8"?>\n<routes>\n')
            out.write(f"    {vtype_xml}\n")
            for _event, el in ET.iterparse(trip_path, events=("end",)):
                if el.tag != "trip":
                    el.clear()
                    continue
                attrs = " ".join(f'{key}="{value}"' for key, value in el.attrib.items())
                out.write(f'    <trip {attrs}/>\n')
                el.clear()
            out.write("</routes>\n")
        staged[vtype_id] = dest
    return staged


def _resolve_dua_iterate_route(step_dir: Path, stem: str, step: int) -> Path:
    plain = step_dir / f"{stem}_{step:03d}.rou.xml"
    gz = step_dir / f"{stem}_{step:03d}.rou.xml.gz"
    if gz.is_file():
        return gz
    if plain.is_file():
        return plain
    raise AssignmentError(f"duaIterate route output missing: {plain} (.gz)")


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
        tree = _parse_routes_file(source)
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
        outputs.append(_resolve_dua_iterate_route(step_dir, trip.stem, last_step))
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

    vtypes_rel = _vtypes_relative(vtypes_xml, assignment_dir)

    if options.method == AssignmentMethod.DUAROUTER:
        trip_arg = trip_files_arg_relative(trip_paths, assignment_dir)
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

    staged_trips = _stage_trips_for_dua_iterate(
        trip_paths,
        vtypes_xml,
        assignment_dir / "staging",
    )
    net_rel = _sumo_path(net_xml, assignment_dir)
    trip_rel = trip_files_arg_relative(staged_trips, assignment_dir)
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
    ]
    code = run_python_tool(script, dua_args, assignment_dir, log_path)
    if code != 0:
        raise AssignmentError(f"duaIterate exited with code {code}; see {log_path}")

    last_iter = last_step - 1
    route_parts = _dua_iterate_output_routes(assignment_dir, staged_trips, last_iter)
    _merge_route_files(route_parts, routes_path)
    return AssignmentResult(
        routes_path=routes_path,
        log_path=log_path,
        returncode=code,
        method=options.method,
        messages=[f"merged {len(route_parts)} route files from iteration {last_iter}"],
    )
