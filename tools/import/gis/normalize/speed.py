# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Per-mode speed resolution from VISUM ``LINKTYPE`` rows.

A SUMO edge carries a single ``speed`` ceiling; per-mode caps are expressed as
``<restriction vClass=... speed=.../>`` on the edge ``type``. Rules are normative
in ``import-network-sqlite`` (``data-inventory.md`` section 5):

* The edge ``speed`` ceiling is the fastest speed among the edge's allowed modes
  (plus ``LINK.V0PRT`` when positive).
* Every allowed ``vClass`` whose ``LINKTYPE`` speed is below the type ceiling
  gets a ``<restriction>`` (all modes, not just bike/pedestrian).
* PuT-only links resolve to a positive ``VDEF_PUTSYS(*)`` speed: no fallback
  table and no epsilon.
* Low speeds are kept (never floored); a coherence warning is logged when a low
  ceiling lands on an edge that allows a motorized class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

# TSYS token -> LINKTYPE per-mode speed column (data-inventory.md section 5).
_PRT_SPEED_FIELD = {
    "CAR": "VMAX_PRTSYS(CAR)",
    "HGV": "VMAX_PRTSYS(HGV)",
    "BIKE": "VMAX_PRTSYS(BIKE)",
    "WALK": "VMAX_PRTSYS(WALK)",
}
_PUT_SPEED_FIELD = {
    "BUS": "VDEF_PUTSYS(BUS)",
    "TRAM": "VDEF_PUTSYS(TRAM)",
    "TRAIN": "VDEF_PUTSYS(TRAIN)",
    "PUTW": "VDEF_PUTSYS(PUTW)",
}
TSYS_SPEED_FIELD: dict[str, str] = {**_PRT_SPEED_FIELD, **_PUT_SPEED_FIELD}

KMH_TO_MS = 1.0 / 3.6

# Default coherence threshold: a ceiling at or below this (km/h) on a motorized
# edge is flagged for inspection (data-inventory.md section 5 step 7).
DEFAULT_LOW_SPEED_THRESHOLD_KMH = 5.0

# vClasses that are NOT motorized; a low ceiling on these alone is expected.
NON_MOTORIZED_VCLASSES = frozenset({"bicycle", "pedestrian"})


@dataclass
class SpeedResolution:
    """Resolved speed for one edge plus the restrictions for its type."""

    speed_ms: float
    ceiling_kmh: float
    restrictions_kmh: dict[str, float] = field(default_factory=dict)
    coherence_warning: bool = False


def _float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def type_mode_speeds(
    linktype_row: Mapping[str, object],
    tsys_to_vclass: Mapping[str, str],
) -> dict[str, float]:
    """Collect positive per-``vClass`` speeds (km/h) offered by a link type.

    Where several TSYS tokens map to the same ``vClass`` (e.g. ``PUTW``/``WALK``
    → ``pedestrian``) the higher speed wins.
    """
    speeds: dict[str, float] = {}
    for token, field_name in TSYS_SPEED_FIELD.items():
        vclass = tsys_to_vclass.get(token.upper())
        if vclass is None:
            continue
        value = _float(linktype_row.get(field_name))
        if value is None or value <= 0:
            continue
        if value > speeds.get(vclass, 0.0):
            speeds[vclass] = value
    return speeds


def resolve_edge_speed(
    allowed_vclasses: list[str],
    linktype_row: Mapping[str, object],
    tsys_to_vclass: Mapping[str, str],
    v0prt_kmh: object = None,
    low_speed_threshold_kmh: float = DEFAULT_LOW_SPEED_THRESHOLD_KMH,
) -> SpeedResolution:
    """Resolve the edge speed ceiling and the per-type per-mode restrictions.

    The ceiling is the fastest speed among ``allowed_vclasses`` (and ``V0PRT``
    when positive). Restrictions cover every allowed ``vClass`` whose link-type
    speed is below the type's own fastest mode, so SUMO caps each class via
    ``min(edge speed, restriction)``.
    """
    type_speeds = type_mode_speeds(linktype_row, tsys_to_vclass)

    candidates = [type_speeds[vc] for vc in allowed_vclasses if vc in type_speeds]
    v0 = _float(v0prt_kmh)
    if v0 is not None and v0 > 0:
        candidates.append(v0)
    ceiling_kmh = max(candidates) if candidates else 0.0

    # Type ceiling = fastest mode the type offers; restrictions are emitted for
    # any allowed mode below it.
    type_ceiling = max(type_speeds.values()) if type_speeds else ceiling_kmh
    restrictions: dict[str, float] = {}
    for vclass in allowed_vclasses:
        mode_speed = type_speeds.get(vclass)
        if mode_speed is not None and mode_speed < type_ceiling:
            restrictions[vclass] = mode_speed

    motorized = any(vc not in NON_MOTORIZED_VCLASSES for vc in allowed_vclasses)
    coherence_warning = (
        motorized and 0.0 < ceiling_kmh <= low_speed_threshold_kmh
    )

    return SpeedResolution(
        speed_ms=ceiling_kmh * KMH_TO_MS,
        ceiling_kmh=ceiling_kmh,
        restrictions_kmh=restrictions,
        coherence_warning=coherence_warning,
    )


# --- GeoJSON path (import-network-geojson data-inventory.md section 5) ---

DEFAULT_LC_FALLBACK_KMH: dict[str, float] = {
    "MAJOR": 70.0,
    "IN-URBAN": 50.0,
    "COLLECTOR": 50.0,
    "RAMP": 50.0,
    "PUT": 50.0,
}
DEFAULT_UNMAPPED_LC_FALLBACK_KMH = 50.0


@dataclass
class GeoJsonSpeedResolution:
    """Speed resolved from GeoJSON ``V0PRT`` and ``LC`` fallback."""

    speed_ms: float
    speed_kmh: float
    substituted: bool = False
    lc: str = ""
    link_no: str = ""


def parse_v0prt_kmh(value: object) -> float | None:
    """Parse VISUM GeoJSON ``V0PRT`` strings such as ``\"30km/h\"`` to km/h."""
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text.endswith("km/h"):
        text = text[:-4].strip()
    try:
        number = float(text)
    except ValueError:
        return None
    return number


def lc_fallback_kmh(
    lc: object,
    fallbacks: Mapping[str, float] | None = None,
) -> float:
    """Return the configured fallback speed (km/h) for a link class."""
    table = DEFAULT_LC_FALLBACK_KMH if fallbacks is None else {
        str(k).upper(): float(v) for k, v in fallbacks.items()
    }
    key = str(lc or "").strip().upper()
    return table.get(key, DEFAULT_UNMAPPED_LC_FALLBACK_KMH)


def resolve_geojson_edge_speed(
    v0prt: object,
    lc: object,
    link_no: object,
    *,
    lc_fallbacks: Mapping[str, float] | None = None,
) -> GeoJsonSpeedResolution:
    """Resolve edge speed from ``V0PRT`` when positive, else ``LC`` fallback."""
    parsed = parse_v0prt_kmh(v0prt)
    link_id = str(link_no)
    lc_text = str(lc or "").strip()
    if parsed is not None and parsed > 0:
        return GeoJsonSpeedResolution(
            speed_ms=parsed * KMH_TO_MS,
            speed_kmh=parsed,
            substituted=False,
            lc=lc_text,
            link_no=link_id,
        )
    fallback = lc_fallback_kmh(lc, lc_fallbacks)
    return GeoJsonSpeedResolution(
        speed_ms=fallback * KMH_TO_MS,
        speed_kmh=fallback,
        substituted=True,
        lc=lc_text,
        link_no=link_id,
    )
