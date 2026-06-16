# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .models import BuildOptions, TransformLog

logger = logging.getLogger(__name__)


def detect_and_reproject(gdf, options: BuildOptions, log: TransformLog, target_epsg: Optional[str] = None):
    import geopandas as gpd
    from pyproj import CRS

    if gdf.crs is None and options.crs:
        gdf = gdf.set_crs(options.crs)
        log.record(f"Applied client CRS override: {options.crs}")
    elif gdf.crs is None:
        raise ValueError("Source CRS missing; supply build_options.crs")

    if target_epsg:
        target = CRS.from_user_input(target_epsg)
        if gdf.crs != target:
            source = gdf.crs.to_string()
            gdf = gdf.to_crs(target_epsg)
            log.record(f"Reprojected from {source} to {target_epsg}")
    return gdf


def read_vector(path: Path, layer: Optional[str] = None):
    import geopandas as gpd

    return gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)


def apply_sqlite_joins(gdf, joins: list[dict[str, str]], sqlite_path: Path, log: TransformLog):
    import geopandas as gpd
    import sqlite3

    if not joins:
        return gdf
    conn = sqlite3.connect(sqlite_path)
    try:
        for spec in joins:
            attr_table = spec["attr_table"]
            key = spec["key"]
            attrs = gpd.read_file(sqlite_path, sql=f'SELECT * FROM "{attr_table}"')
            gdf = gdf.merge(attrs, on=key, how="left")
            log.record(f"Joined {attr_table} on {key}")
    finally:
        conn.close()
    return gdf


def zone_id_column(gdf) -> str:
    for col in ("zone_id", "id", "ID", "ZONE_ID"):
        if col in gdf.columns:
            return col
    raise ValueError("Zone layer requires zone_id or id column")


def export_layer(gdf, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path)
    return path
