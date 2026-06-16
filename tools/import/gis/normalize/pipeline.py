# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .crs import (
    apply_sqlite_joins,
    detect_and_reproject,
    export_layer,
    read_vector,
    zone_id_column,
)
from .models import BuildOptions, NormalizedLayers, TransformLog


def _layer_map_path(paths_root: Path) -> Path:
    return paths_root / "inputs" / "layer_map.json"


def normalize_inputs(
    inputs_dir: Path,
    build_dir: Path,
    options: BuildOptions,
    layer_overrides: Optional[dict[str, str]] = None,
) -> NormalizedLayers:
    """Read uploads and export preprocess artifacts for netconvert/polyconvert."""
    log = TransformLog()
    result = NormalizedLayers(transform_log=log)
    layers = dict(options.layers)
    if layer_overrides:
        layers.update(layer_overrides)

    manifest = _load_manifest(inputs_dir)
    target_crs = options.crs

    for entry in manifest:
        path = inputs_dir / entry["filename"]
        role = entry.get("role", "")
        layer = entry.get("layer") or layers.get(role)
        suffix = path.suffix.lower()

        if suffix in (".geojson", ".json", ".gpkg", ".shp"):
            gdf = read_vector(path, layer=layer if suffix == ".gpkg" else None)
            if target_crs:
                gdf = detect_and_reproject(gdf, options, log, target_epsg=target_crs)
            elif gdf.crs is not None:
                target_crs = gdf.crs.to_string()
                log.record(f"Auto-detected CRS: {target_crs}")

            if role == "roads" or layers.get("roads") == layer:
                result.roads_path = export_layer(gdf, build_dir / "roads.shp")
            elif role == "zones" or layer == layers.get("zones", "zones"):
                result.zones_path = export_layer(gdf, build_dir / "zones.shp")
                col = zone_id_column(gdf)
                result.zone_ids = {str(v) for v in gdf[col].tolist()}
        elif suffix in (".sqlite", ".db"):
            gdf = read_vector(path, layer=layer)
            gdf = apply_sqlite_joins(gdf, options.sqlite_joins, path, log)
            if target_crs:
                gdf = detect_and_reproject(gdf, options, log, target_epsg=target_crs)
            if role == "zones" or layer == layers.get("zones", "zones"):
                result.zones_path = export_layer(gdf, build_dir / "zones.shp")
                col = zone_id_column(gdf)
                result.zone_ids = {str(v) for v in gdf[col].tolist()}
            else:
                result.roads_path = export_layer(gdf, build_dir / "roads.shp")

    if result.roads_path is None:
        for path in inputs_dir.iterdir():
            if path.suffix.lower() in (".geojson", ".gpkg", ".shp"):
                gdf = read_vector(path)
                result.roads_path = export_layer(gdf, build_dir / "roads.shp")
                break

    log_path = build_dir / "crs_transforms.log"
    log_path.write_text("\n".join(log.messages), encoding="utf-8")
    return result


def _load_manifest(inputs_dir: Path) -> list[dict]:
    manifest_path = inputs_dir / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return [{"filename": p.name, "role": _guess_role(p)} for p in inputs_dir.iterdir() if p.is_file()]


def _guess_role(path: Path) -> str:
    name = path.stem.lower()
    if "zone" in name or name == "zones":
        return "zones"
    if "omx" in name:
        return "omx"
    return "roads"
