# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Read VISUM GeoJSON node/link exports and normalize them for ``netconvert``.

Implements the ``import-network-geojson`` capability: WGS84 point/line geometry,
directional AB/BA split from ``R_*`` fields, ``TSYSSET`` → ``vClass`` permissions,
``V0PRT`` + ``LC`` speed resolution, and edge-type assignment from ``LC``.

Translation rules are normative in ``import-network-geojson/data-inventory.md``.
This module performs no subprocess work; ``orchestrate/netbuild.py`` consumes the
:class:`NormalizedNetwork` it produces.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional

from .modes import DEFAULT_MODE_MAPPING, map_tsysset
from .speed import (
    DEFAULT_LC_FALLBACK_KMH,
    resolve_geojson_edge_speed,
)
from .visum_sqlite import (
    EdgeRecord,
    NodeRecord,
    NormalizedNetwork,
)

DEFAULT_SOURCE_EPSG = "EPSG:4326"


class VisumGeoJsonError(RuntimeError):
    """Raised on unreadable input or unresolved CRS."""


@dataclass
class GeoJsonBuildOptions:
    """Options for a VISUM GeoJSON network build (data-inventory sections 4-7)."""

    mode_mapping: dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_MODE_MAPPING)
    )
    source_crs: str = DEFAULT_SOURCE_EPSG
    lc_fallbacks: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_LC_FALLBACK_KMH)
    )


def _load_geojson(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise VisumGeoJsonError(
            f"Could not read GeoJSON file {path}: {exc}"
        ) from exc


def _feature_crs(data: dict, options: GeoJsonBuildOptions) -> str:
    crs_obj = data.get("crs")
    if isinstance(crs_obj, dict):
        props = crs_obj.get("properties") or {}
        name = props.get("name") or props.get("code")
        if name:
            text = str(name)
            if text.upper().startswith("EPSG:"):
                return text
            if "CRS84" in text or "4326" in text:
                return DEFAULT_SOURCE_EPSG
    if options.source_crs:
        return options.source_crs
    raise VisumGeoJsonError(
        "GeoJSON CRS is missing or ambiguous; supply build_options.source_crs"
    )


def _coords_xy(geometry: dict) -> list[tuple[float, float]]:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
        return [(float(coords[0]), float(coords[1]))]
    if gtype == "LineString" and isinstance(coords, list):
        return [(float(c[0]), float(c[1])) for c in coords if len(c) >= 2]
    return []


def _dedupe_consecutive(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not points:
        return points
    out = [points[0]]
    for pt in points[1:]:
        if pt != out[-1]:
            out.append(pt)
    return out


def _read_nodes(
    path: Path,
    options: GeoJsonBuildOptions,
    result: NormalizedNetwork,
) -> dict[str, tuple[float, float]]:
    data = _load_geojson(path)
    result.source_wkt = _feature_crs(data, options)
    result.target_epsg = result.source_wkt or options.source_crs
    node_xy: dict[str, tuple[float, float]] = {}
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        if "NO" not in props:
            continue
        node_id = str(props["NO"])
        geom = feature.get("geometry") or {}
        coords = _coords_xy(geom)
        if not coords:
            result.record(f"Node {node_id} has no point geometry; skipped")
            continue
        x, y = coords[0]
        node_xy[node_id] = (x, y)
        result.nodes.append(NodeRecord(node_id=node_id, x=x, y=y))
    if not node_xy:
        raise VisumGeoJsonError(f"No node features found in {path}")
    return node_xy


def _directional_value(props: Mapping[str, object], ab_key: str, ba_key: str, reverse: bool):
    return props.get(ba_key if reverse else ab_key)


def _edge_type_id(lc: object, typeno: object) -> str:
    lc_text = str(lc or "").strip()
    if lc_text:
        return lc_text
    if typeno is not None and str(typeno).strip():
        return str(typeno)
    return "default"


def _emit_direction(
    props: Mapping[str, object],
    reverse: bool,
    geometry: list[tuple[float, float]],
    options: GeoJsonBuildOptions,
    node_xy: Mapping[str, tuple[float, float]],
    result: NormalizedNetwork,
) -> None:
    no = _directional_value(props, "NO", "R_NO", reverse)
    from_node = str(_directional_value(props, "FROMNODENO", "R_FROMNODENO", reverse))
    to_node = str(_directional_value(props, "TONODENO", "R_TONODENO", reverse))
    tsysset = _directional_value(props, "TSYSSET", "R_TSYSSET", reverse)
    num_lanes = _directional_value(props, "NUMLANES", "R_NUMLANES", reverse)
    v0prt = _directional_value(props, "V0PRT", "R_V0PRT", reverse)
    lc = _directional_value(props, "LC", "R_LC", reverse)
    typeno = _directional_value(props, "TYPENO", "R_TYPENO", reverse)
    direction = "BA" if reverse else "AB"
    link_no = str(no)

    vclasses, unmapped = map_tsysset(tsysset, options.mode_mapping)
    for token in unmapped:
        result.unmapped_tokens[token] = result.unmapped_tokens.get(token, 0) + 1

    if not vclasses:
        result.skipped_directions.append(f"{link_no}:{direction}")
        return

    if from_node not in node_xy or to_node not in node_xy:
        result.record(
            f"Link {link_no}:{direction} references missing node coordinates; skipped"
        )
        result.skipped_directions.append(f"{link_no}:{direction}")
        return

    resolution = resolve_geojson_edge_speed(
        v0prt, lc, link_no, lc_fallbacks=options.lc_fallbacks
    )
    if resolution.substituted:
        result.speed_substitutions.append(resolution)
        result.record(
            f"Speed substitution link={link_no} LC={resolution.lc!r} "
            f"applied={resolution.speed_kmh:g}km/h"
        )

    lanes = int(num_lanes) if num_lanes not in (None, "") else 1
    lanes = max(lanes, 1)
    edge_id = f"-{link_no}" if reverse else link_no

    if reverse:
        shape = list(reversed(geometry)) if geometry else []
    else:
        shape = list(geometry) if geometry else []

    if not shape:
        shape = [node_xy[from_node], node_xy[to_node]]
    else:
        shape = _dedupe_consecutive(shape)
        if shape[0] != node_xy[from_node]:
            shape = [node_xy[from_node], *shape]
        if shape[-1] != node_xy[to_node]:
            shape = [*shape, node_xy[to_node]]
        shape = _dedupe_consecutive(shape)

    type_id = _edge_type_id(lc, typeno)
    result.edges.append(
        EdgeRecord(
            edge_id=edge_id,
            from_node=from_node,
            to_node=to_node,
            type_id=type_id,
            num_lanes=lanes,
            speed_ms=resolution.speed_ms,
            allow=vclasses,
            shape=shape,
        )
    )


def normalize_geojson_network(
    nodes_path: str | Path,
    links_path: str | Path,
    options: Optional[GeoJsonBuildOptions] = None,
) -> NormalizedNetwork:
    """Read and normalize VISUM GeoJSON node/link files into network records."""
    options = options or GeoJsonBuildOptions()
    nodes_path = Path(nodes_path)
    links_path = Path(links_path)
    if not nodes_path.is_file():
        raise VisumGeoJsonError(f"Node GeoJSON path is not a file: {nodes_path}")
    if not links_path.is_file():
        raise VisumGeoJsonError(f"Link GeoJSON path is not a file: {links_path}")

    result = NormalizedNetwork(target_epsg=options.source_crs)
    node_xy = _read_nodes(nodes_path, options, result)

    link_data = _load_geojson(links_path)
    link_crs = _feature_crs(link_data, options)
    if result.source_wkt and link_crs != result.source_wkt:
        result.record(
            f"Link CRS {link_crs!r} differs from node CRS {result.source_wkt!r}; "
            f"using node CRS"
        )
    result.target_epsg = result.source_wkt or link_crs

    for feature in link_data.get("features") or []:
        props = feature.get("properties") or {}
        if "NO" not in props:
            continue
        geom = feature.get("geometry") or {}
        geometry = _coords_xy(geom)
        _emit_direction(props, reverse=False, geometry=geometry, options=options,
                         node_xy=node_xy, result=result)
        _emit_direction(props, reverse=True, geometry=geometry, options=options,
                         node_xy=node_xy, result=result)

    if not result.edges:
        raise VisumGeoJsonError("No edges emitted from link GeoJSON")
    return result
