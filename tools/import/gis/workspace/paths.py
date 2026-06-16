# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def workspace_root() -> Path:
    return Path(os.environ.get("GIS_API_WORKSPACE", "scenarios")).resolve()


@dataclass(frozen=True)
class ScenarioPaths:
    scenario_id: str
    root: Path

    @classmethod
    def create(cls, scenario_id: str, root: Path | None = None) -> "ScenarioPaths":
        base = (root or workspace_root()) / scenario_id
        paths = cls(scenario_id=scenario_id, root=base)
        paths.ensure()
        return paths

    def ensure(self) -> None:
        for sub in (self.inputs, self.build, self.logs, self.runs):
            sub.mkdir(parents=True, exist_ok=True)

    @property
    def inputs(self) -> Path:
        return self.root / "inputs"

    @property
    def build(self) -> Path:
        return self.root / "build"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    @property
    def status_file(self) -> Path:
        return self.root / "status.json"

    def run_dir(self, run_id: str) -> Path:
        path = self.runs / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list_artifacts(self) -> list[str]:
        names: list[str] = []
        for folder in (self.build, self.logs, self.runs):
            if not folder.exists():
                continue
            for path in folder.rglob("*"):
                if path.is_file():
                    names.append(str(path.relative_to(self.root)))
        return sorted(names)
