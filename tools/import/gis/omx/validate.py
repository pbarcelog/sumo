# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations


def validate_zone_ids(omx_zones: set[str], polygon_zones: set[str]) -> None:
    if not polygon_zones and omx_zones:
        raise ValueError("OMX references zones but no zone polygons were supplied")
    unknown = omx_zones - polygon_zones
    if unknown:
        raise ValueError(
            f"OMX zone ids not present in zones layer (strict match): {sorted(unknown)}"
        )


def validate_zone_alignment(
    omx_zones: set[str],
    zone_table_ids: set[str],
    taz_ids: set[str],
) -> None:
    """Strict OMX ↔ ZONE ↔ tazs alignment (ADR-014, fail-loud)."""
    missing_in_zone = omx_zones - zone_table_ids
    if missing_in_zone:
        raise ValueError(
            f"OMX zone ids absent from ZONE table: {sorted(missing_in_zone)}"
        )
    extra_tazs = taz_ids - zone_table_ids
    if extra_tazs:
        raise ValueError(f"tazs ids absent from ZONE table: {sorted(extra_tazs)}")


def validate_demand_bearing_tazs(
    demand_zone_ids: set[str],
    taz_ids: set[str],
) -> None:
    missing = demand_zone_ids - taz_ids
    if missing:
        raise ValueError(
            f"demand-bearing zones missing from tazs: {sorted(missing)}"
        )
