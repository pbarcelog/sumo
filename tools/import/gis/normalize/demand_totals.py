# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Per-zone OMX demand totals used for connector synthesis and fail-loud checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ZoneDemandTotals:
    external_production: float = 0.0
    external_attraction: float = 0.0
    intrazonal: float = 0.0

    @property
    def needs_outbound(self) -> bool:
        return self.external_production > 0

    @property
    def needs_inbound(self) -> bool:
        return self.external_attraction > 0

    @property
    def has_external(self) -> bool:
        return self.needs_outbound or self.needs_inbound


def zone_demand_totals_by_core(
    omx_path: str | Path,
    cores: tuple[str, ...],
    *,
    mapping_name: str = "NO",
) -> dict[str, dict[str, ZoneDemandTotals]]:
    import openmatrix as omx

    result: dict[str, dict[str, ZoneDemandTotals]] = {core: {} for core in cores}
    with omx.open_file(str(omx_path), "r") as f:
        keymap = f.mapping(mapping_name)
        size = max(keymap.values()) + 1
        labels: list[str | None] = [None] * size
        for label, index in keymap.items():
            labels[index] = str(label)

        for core in cores:
            if core not in f.list_matrices():
                continue
            matrix = f[core]
            for index, zone_id in enumerate(labels):
                if zone_id is None:
                    continue
                intra = float(matrix[index, index])
                ext_prod = sum(float(matrix[index, j]) for j in range(size) if j != index)
                ext_attr = sum(float(matrix[j, index]) for j in range(size) if j != index)
                result[core][zone_id] = ZoneDemandTotals(
                    external_production=ext_prod,
                    external_attraction=ext_attr,
                    intrazonal=intra,
                )
    return result
