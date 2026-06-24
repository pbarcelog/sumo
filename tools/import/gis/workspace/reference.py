# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Reference workspace layout for local VISUM scenarios (ADR-015)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScenarioReferenceLayout:
    """Staged directories for OMX + SQLite demand and assignment builds."""

    root: Path

    @classmethod
    def create(cls, root: str | Path) -> "ScenarioReferenceLayout":
        layout = cls(root=Path(root).resolve())
        layout.ensure()
        return layout

    def ensure(self) -> None:
        for sub in (
            self.sources,
            self.network,
            self.demand,
            self.assignment,
            self.sim,
        ):
            sub.mkdir(parents=True, exist_ok=True)

    @property
    def sources(self) -> Path:
        return self.root / "sources"

    @property
    def network(self) -> Path:
        return self.root / "network"

    @property
    def demand(self) -> Path:
        return self.root / "demand"

    @property
    def assignment(self) -> Path:
        return self.root / "assignment"

    @property
    def sim(self) -> Path:
        return self.root / "sim"

    @property
    def manifest_path(self) -> Path:
        return self.root / "build-manifest.json"

    @property
    def net_xml(self) -> Path:
        return self.network / "net.net.xml"

    @property
    def routes_xml(self) -> Path:
        return self.assignment / "routes.xml"

    @property
    def vtypes_xml(self) -> Path:
        return self.sim / "vtypes.add.xml"
