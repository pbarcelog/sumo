# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class BuildState(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"


class RunState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScenarioStatus:
    state: BuildState = BuildState.PENDING
    step: str = ""
    progress: float = 0.0
    error: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


@dataclass
class RunStatus:
    run_id: str
    state: RunState = RunState.PENDING
    step: str = ""
    error: Optional[dict[str, Any]] = None
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


class StatusStore:
    def __init__(self, status_file: Path) -> None:
        self._path = status_file

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"build": ScenarioStatus().to_dict(), "runs": {}}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_build(self) -> ScenarioStatus:
        raw = self.load().get("build", {})
        return ScenarioStatus(
            state=BuildState(raw.get("state", BuildState.PENDING.value)),
            step=raw.get("step", ""),
            progress=float(raw.get("progress", 0.0)),
            error=raw.get("error"),
        )

    def set_build(self, status: ScenarioStatus) -> None:
        data = self.load()
        data["build"] = status.to_dict()
        self.save(data)

    def get_run(self, run_id: str) -> Optional[RunStatus]:
        raw = self.load().get("runs", {}).get(run_id)
        if raw is None:
            return None
        return RunStatus(
            run_id=run_id,
            state=RunState(raw.get("state", RunState.PENDING.value)),
            step=raw.get("step", ""),
            error=raw.get("error"),
            artifacts=list(raw.get("artifacts", [])),
        )

    def set_run(self, status: RunStatus) -> None:
        data = self.load()
        runs = data.setdefault("runs", {})
        runs[status.run_id] = status.to_dict()
        self.save(data)
