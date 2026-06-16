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
