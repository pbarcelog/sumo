# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Build manifest fingerprints and invalidation (demand-assignment)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import sumolib


class RebuildPlan(str, Enum):
    FULL = "full"
    ASSIGNMENT_ONLY = "assignment_only"
    SKIP = "skip"


@dataclass
class InputFingerprints:
    omx: str
    sqlite: str
    net_xml: str


@dataclass
class AssignmentFingerprint:
    method: str
    iterations: int
    begin: int
    end: int


@dataclass
class BuildManifest:
    version: int = 1
    created_at: str = ""
    sumo_version: str = ""
    inputs: Optional[InputFingerprints] = None
    assignment: Optional[AssignmentFingerprint] = None
    artifacts: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildManifest":
        inputs = data.get("inputs")
        assignment = data.get("assignment")
        return cls(
            version=int(data.get("version", 1)),
            created_at=str(data.get("created_at", "")),
            sumo_version=str(data.get("sumo_version", "")),
            inputs=InputFingerprints(**inputs) if inputs else None,
            assignment=AssignmentFingerprint(**assignment) if assignment else None,
            artifacts=dict(data.get("artifacts", {})),
        )


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: str | Path) -> Optional[BuildManifest]:
    manifest_path = Path(path)
    if not manifest_path.is_file():
        return None
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return BuildManifest.from_dict(data)


def save_manifest(path: str | Path, manifest: BuildManifest) -> None:
    manifest_path = Path(path)
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sumo_version() -> str:
    try:
        return str(sumolib.version.gitDescribe())
    except Exception:
        return "unknown"


def build_manifest(
    *,
    omx: Path,
    sqlite: Path,
    net_xml: Path,
    assignment_method: str,
    assignment_iterations: int,
    assignment_begin: int,
    assignment_end: int,
    artifacts: dict[str, str],
) -> BuildManifest:
    return BuildManifest(
        created_at=datetime.now(timezone.utc).isoformat(),
        sumo_version=_sumo_version(),
        inputs=InputFingerprints(
            omx=sha256_file(omx),
            sqlite=sha256_file(sqlite),
            net_xml=sha256_file(net_xml),
        ),
        assignment=AssignmentFingerprint(
            method=assignment_method,
            iterations=assignment_iterations,
            begin=assignment_begin,
            end=assignment_end,
        ),
        artifacts=artifacts,
    )


def plan_rebuild(
    existing: Optional[BuildManifest],
    *,
    omx: Path,
    sqlite: Path,
    net_xml: Path,
    assignment_method: str,
    assignment_iterations: int,
    assignment_begin: int,
    assignment_end: int,
    trips_exist: bool,
    routes_exist: bool,
) -> RebuildPlan:
    if existing is None or existing.inputs is None:
        return RebuildPlan.FULL

    new_inputs = InputFingerprints(
        omx=sha256_file(omx),
        sqlite=sha256_file(sqlite),
        net_xml=sha256_file(net_xml),
    )
    new_assignment = AssignmentFingerprint(
        method=assignment_method,
        iterations=assignment_iterations,
        begin=assignment_begin,
        end=assignment_end,
    )

    demand_changed = (
        new_inputs.omx != existing.inputs.omx
        or new_inputs.sqlite != existing.inputs.sqlite
    )
    net_changed = new_inputs.net_xml != existing.inputs.net_xml
    assignment_changed = (
        existing.assignment is None
        or new_assignment != existing.assignment
    )

    if demand_changed:
        return RebuildPlan.FULL
    if net_changed or assignment_changed:
        if not trips_exist:
            return RebuildPlan.FULL
        return RebuildPlan.ASSIGNMENT_ONLY
    if routes_exist:
        return RebuildPlan.SKIP
    if trips_exist:
        return RebuildPlan.ASSIGNMENT_ONLY
    return RebuildPlan.FULL
