# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Read VISUM GeoJSON zone centroids and connectors for demand import.

Expands ``connector.geojson`` AB + ``R_*`` rows into the same ``ConnectorRow`` contract as
SQLite ``CONNECTOR``. Translation rules are normative in
``import-od-demand-geojson/data-inventory.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

from .modes import split_tsysset
from .visum_zones import (
    ConnectorRow,
    VisumZonesError,
    ZoneConnectorTables,
    _classify_put_only_zones,
)


def _load_geojson(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise VisumZonesError(f"Could not read GeoJSON file {path}: {exc}") from exc


def _directional_value(props: dict, ab_key: str, ba_key: str, reverse: bool):
    return props.get(ba_key if reverse else ab_key)


def _emit_connector_row(
    props: dict,
    reverse: bool,
    connectors: list[ConnectorRow],
    skipped: list[str],
) -> None:
    zoneno = _directional_value(props, "ZONENO", "R_ZONENO", reverse)
    nodeno = _directional_value(props, "NODENO", "R_NODENO", reverse)
    direction = _directional_value(props, "DIRECTION", "R_DIRECTION", reverse)
    tsysset = _directional_value(props, "TSYSSET", "R_TSYSSET", reverse)

    if zoneno is None or nodeno is None or not direction:
        return

    tokens = split_tsysset(tsysset)
    if not tokens:
        skipped.append(f"{zoneno}:{direction}:empty-TSYSSET")
        return

    connectors.append(
        (int(zoneno), int(nodeno), str(direction), str(tsysset or ""))
    )


def read_zone_connectors_from_geojson(
    zone_centroid_path: str | Path,
    connector_path: str | Path,
) -> tuple[ZoneConnectorTables, list[str]]:
    """Read zone ids and expanded connector rows from GeoJSON exports."""
    zone_centroid_path = Path(zone_centroid_path)
    connector_path = Path(connector_path)
    if not zone_centroid_path.is_file():
        raise VisumZonesError(f"Zone centroid GeoJSON path is not a file: {zone_centroid_path}")
    if not connector_path.is_file():
        raise VisumZonesError(f"Connector GeoJSON path is not a file: {connector_path}")

    zone_data = _load_geojson(zone_centroid_path)
    zone_ids: set[str] = set()
    for feature in zone_data.get("features") or []:
        props = feature.get("properties") or {}
        if "NO" not in props:
            continue
        zone_ids.add(str(props["NO"]))
    if not zone_ids:
        raise VisumZonesError(f"No zone features found in {zone_centroid_path}")

    connectors: list[ConnectorRow] = []
    skipped: list[str] = []
    link_data = _load_geojson(connector_path)
    for feature in link_data.get("features") or []:
        props = feature.get("properties") or {}
        _emit_connector_row(props, reverse=False, connectors=connectors, skipped=skipped)
        _emit_connector_row(props, reverse=True, connectors=connectors, skipped=skipped)

    if not connectors:
        raise VisumZonesError(f"No connector rows emitted from {connector_path}")

    unknown_zones = {str(c[0]) for c in connectors} - zone_ids
    if unknown_zones:
        raise VisumZonesError(
            f"Connector references unknown zone id(s): {sorted(unknown_zones, key=int)}"
        )

    put_only = _classify_put_only_zones(zone_ids, connectors)
    return (
        ZoneConnectorTables(
            zone_ids=zone_ids,
            connectors=connectors,
            put_only_zones=put_only,
        ),
        skipped,
    )
