# gis-normalization

GIS input normalization before SUMO binaries (ADR-011, ADR-013).

**PRD:** §2, §4

## ADDED Requirements

### Requirement: Read GeoJSON and GeoPackage via pyogrio

The normalizer SHALL read GeoJSON and GPKG layers using geopandas and pyogrio in `tools/import/gis/normalize/`. ADR-011.

#### Scenario: GeoJSON roads layer

- **WHEN** client supplies GeoJSON with line geometries
- **THEN** normalizer exports a format netconvert accepts for network build

### Requirement: CRS auto-detect and reproject

The normalizer SHALL auto-detect source CRS when present, accept optional `build_options.crs` override, reproject to network CRS before netconvert, and log every transform. PRD §4.

#### Scenario: Reprojection logged

- **WHEN** source CRS differs from target network CRS
- **THEN** build log records source EPSG, target EPSG, and transform applied

### Requirement: SQLite SpatiaLite and attribute joins

The normalizer SHALL read SpatiaLite geometry tables via pyogrio and join plain attribute tables when `build_options.sqlite_joins` is supplied. ADR-013.

#### Scenario: Full SQLite model

- **WHEN** database contains geometry and attribute tables with shared `zone_id`
- **THEN** normalizer produces joined features for downstream TAZ and demand steps

### Requirement: Zone polygon layer convention

The normalizer SHALL default to layer/table name `zones` for TAZ polygons, overridable via `build_options.layers.zones` or `?layer=`. ADR-014.

#### Scenario: Default zones layer

- **WHEN** GPKG contains layer `zones` and no override is set
- **THEN** normalizer selects `zones` for TAZ polygon extraction

### Requirement: Fail loud on read errors

The normalizer SHALL return explicit errors on GDAL/pyogrio read failures without silent drops. PRD §4.

#### Scenario: Invalid GPKG

- **WHEN** uploaded GPKG cannot be opened
- **THEN** build fails with error code and message in scenario status
