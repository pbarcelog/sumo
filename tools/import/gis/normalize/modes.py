# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""VISUM transport-system (``TSYS``) token to SUMO ``vClass`` translation.

Translation rules are normative in the change ``import-network-sqlite``
(``data-inventory.md`` section 4). Used by both the GeoJSON and SQLite VISUM
network importers.
"""

from __future__ import annotations

from typing import Iterable, Mapping

# data-inventory.md section 4 (Karlsruhe sign-off 2026-06-18).
DEFAULT_MODE_MAPPING: dict[str, str] = {
    "CAR": "passenger",
    "HGV": "truck",
    "BIKE": "bicycle",
    "BUS": "bus",
    "TRAM": "tram",
    "TRAIN": "rail_urban",
    "PUTW": "pedestrian",
    "WALK": "pedestrian",
}


def split_tsysset(value: object) -> list[str]:
    """Split a comma-separated ``TSYSSET`` value into upper-case tokens."""
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    return [token.strip().upper() for token in text.split(",") if token.strip()]


def map_tsysset(
    value: object,
    mapping: Mapping[str, str] | None = None,
) -> tuple[list[str], list[str]]:
    """Map a ``TSYSSET`` value to ordered, de-duplicated SUMO ``vClass`` names.

    Returns ``(vclasses, unmapped_tokens)``. ``vclasses`` preserves first-seen
    order; ``unmapped_tokens`` lists tokens absent from the mapping so callers
    can report them rather than silently dropping the information.
    """
    table = _normalized_mapping(mapping)
    vclasses: list[str] = []
    unmapped: list[str] = []
    for token in split_tsysset(value):
        mapped = table.get(token)
        if mapped is None:
            if token not in unmapped:
                unmapped.append(token)
            continue
        if mapped not in vclasses:
            vclasses.append(mapped)
    return vclasses, unmapped


def allow_attribute(vclasses: Iterable[str]) -> str:
    """Render a SUMO ``allow`` attribute string from mapped vClasses."""
    return " ".join(vclasses)


def _normalized_mapping(mapping: Mapping[str, str] | None) -> dict[str, str]:
    source = DEFAULT_MODE_MAPPING if mapping is None else mapping
    return {str(key).upper(): str(value) for key, value in source.items()}
