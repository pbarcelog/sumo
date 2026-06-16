# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class BuildOptions:
    crs: Optional[str] = None
    layers: dict[str, str] = field(
        default_factory=lambda: {"zones": "zones", "roads": "roads"}
    )
    sqlite_joins: list[dict[str, str]] = field(default_factory=list)
    vType: str = "DEFAULT_VEHTYPE"

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "BuildOptions":
        if not data:
            return cls()
        return cls(
            crs=data.get("crs"),
            layers=dict(data.get("layers") or {"zones": "zones", "roads": "roads"}),
            sqlite_joins=list(data.get("sqlite_joins") or []),
            vType=data.get("vType", "DEFAULT_VEHTYPE"),
        )


@dataclass
class TransformLog:
    messages: list[str] = field(default_factory=list)

    def record(self, message: str) -> None:
        self.messages.append(message)


@dataclass
class NormalizedLayers:
    roads_path: Optional[Path] = None
    zones_path: Optional[Path] = None
    zone_ids: set[str] = field(default_factory=set)
    transform_log: TransformLog = field(default_factory=TransformLog)
