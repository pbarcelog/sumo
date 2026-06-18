# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""Builders for compact synthetic VISUM SQLite fixtures.

Each fixture encodes the translation rules from
``openspec/changes/import-network-sqlite/data-inventory.md`` so unit tests do not
need the 31.8 MB real Karlsruhe database.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# The real Karlsruhe NETWORK.PROJECTIONDEFINITION (sphere Mercator, ESRI).
SPHERE_MERCATOR_WKT = (
    'PROJCS["Sphere_Mercator",GEOGCS["GCS_Sphere",DATUM["D_Sphere",'
    'SPHEROID["Sphere",6371000,0]],PRIMEM["Greenwich",0],'
    'UNIT["Degree",0.017453292519943295]],PROJECTION["Mercator"],'
    'PARAMETER["False_Easting",0],PARAMETER["False_Northing",0],'
    'PARAMETER["Central_Meridian",0],PARAMETER["Standard_Parallel_1",0],'
    'UNIT["Meter",1]]'
)

_LINKTYPE_SPEED_COLS = [
    "VMAX_PRTSYS(CAR)", "VMAX_PRTSYS(HGV)", "VMAX_PRTSYS(BIKE)", "VMAX_PRTSYS(WALK)",
    "VDEF_PUTSYS(BUS)", "VDEF_PUTSYS(TRAM)", "VDEF_PUTSYS(TRAIN)", "VDEF_PUTSYS(PUTW)",
]

# Link types: id -> {speed-field: km/h}. Missing field defaults to 0 (not offered).
DEFAULT_LINKTYPES = {
    1: {"VMAX_PRTSYS(CAR)": 50, "VMAX_PRTSYS(HGV)": 30, "VMAX_PRTSYS(BIKE)": 15,
        "VMAX_PRTSYS(WALK)": 5, "VDEF_PUTSYS(BUS)": 45, "VDEF_PUTSYS(TRAM)": 50,
        "VDEF_PUTSYS(TRAIN)": 50, "VDEF_PUTSYS(PUTW)": 5},
    8: {"VMAX_PRTSYS(CAR)": 0, "VMAX_PRTSYS(HGV)": 0, "VMAX_PRTSYS(BIKE)": 0,
        "VMAX_PRTSYS(WALK)": 0, "VDEF_PUTSYS(BUS)": 50, "VDEF_PUTSYS(TRAM)": 50,
        "VDEF_PUTSYS(TRAIN)": 50, "VDEF_PUTSYS(PUTW)": 3},
    90: {"VMAX_PRTSYS(CAR)": 5, "VMAX_PRTSYS(HGV)": 5, "VMAX_PRTSYS(BIKE)": 5,
         "VMAX_PRTSYS(WALK)": 5, "VDEF_PUTSYS(BUS)": 50, "VDEF_PUTSYS(TRAM)": 50,
         "VDEF_PUTSYS(TRAIN)": 50, "VDEF_PUTSYS(PUTW)": 5},
}

# Nodes in sphere-Mercator metres (near Karlsruhe).
DEFAULT_NODES = {
    1: (934000.0, 6266000.0),
    2: (934500.0, 6266100.0),
    3: (935000.0, 6266300.0),
    4: (935500.0, 6266600.0),
}

# (NO, FROMNODENO, TONODENO, TSYSSET, TYPENO, NUMLANES, V0PRT)
DEFAULT_LINKS = [
    (100, 1, 2, "BIKE,CAR,HGV", 1, 2, 50.0),   # bidirectional car link (AB)
    (100, 2, 1, "BIKE,CAR,HGV", 1, 2, 50.0),   # reverse
    (200, 2, 3, "BIKE,CAR,HGV", 1, 1, 50.0),   # one-way: AB populated
    (200, 3, 2, "", 1, 0, 0.0),                # one-way: BA empty -> skipped
    (300, 3, 4, "BUS,TRAIN,TRAM", 8, 1, 0.0),  # PuT-only, V0PRT=0
    (300, 4, 3, "BUS,TRAIN,TRAM", 8, 1, 0.0),
    (500, 1, 3, "CAR,HGV", 90, 1, 5.0),        # low motorized ceiling -> coherence warn
    (600, 1, 4, "CAR,FERRY", 1, 1, 50.0),      # unmapped token FERRY
    (700, 2, 4, "", 1, 0, 0.0),                # fully closed
    (700, 4, 2, "", 1, 0, 0.0),
]

# LINKPOLY vertices for link 100 forward direction (1->2).
DEFAULT_LINKPOLYS = [
    (1, 2, 1, 934100.0, 6266030.0),
    (1, 2, 2, 934300.0, 6266070.0),
]


def create_sqlite(
    path: str | Path,
    *,
    projection: str | None = SPHERE_MERCATOR_WKT,
    nodes=None,
    links=None,
    linktypes=None,
    linkpolys=None,
    include_tables=("NETWORK", "NODE", "LINK", "LINKTYPE", "TSYS", "LINKPOLY"),
    extra_tables=(),
) -> Path:
    """Create a synthetic VISUM SQLite export and return its path."""
    path = Path(path)
    nodes = DEFAULT_NODES if nodes is None else nodes
    links = DEFAULT_LINKS if links is None else links
    linktypes = DEFAULT_LINKTYPES if linktypes is None else linktypes
    linkpolys = DEFAULT_LINKPOLYS if linkpolys is None else linkpolys

    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        if "NETWORK" in include_tables:
            cur.execute("CREATE TABLE NETWORK (PROJECTIONDEFINITION TEXT, UNIT TEXT)")
            cur.execute("INSERT INTO NETWORK VALUES (?, ?)", (projection, "KM"))
        if "TSYS" in include_tables:
            cur.execute("CREATE TABLE TSYS (CODE TEXT, NAME TEXT, TYPE TEXT)")
            for code, typ in [("CAR", "PrT"), ("HGV", "PrT"), ("BIKE", "PrT"),
                              ("BUS", "PuT"), ("TRAM", "PuT"), ("TRAIN", "PuT"),
                              ("PUTW", "PuTWalk"), ("WALK", "PrT")]:
                cur.execute("INSERT INTO TSYS VALUES (?, ?, ?)", (code, code, typ))
        if "NODE" in include_tables:
            cur.execute("CREATE TABLE NODE (NO INTEGER PRIMARY KEY, XCOORD DOUBLE, YCOORD DOUBLE)")
            for no, (x, y) in nodes.items():
                cur.execute("INSERT INTO NODE VALUES (?, ?, ?)", (no, x, y))
        if "LINKTYPE" in include_tables:
            cols = ", ".join(f'"{c}" DOUBLE' for c in _LINKTYPE_SPEED_COLS)
            cur.execute(f"CREATE TABLE LINKTYPE (NO INTEGER PRIMARY KEY, {cols})")
            placeholders = ", ".join("?" for _ in range(1 + len(_LINKTYPE_SPEED_COLS)))
            for no, speeds in linktypes.items():
                values = [no] + [speeds.get(c, 0.0) for c in _LINKTYPE_SPEED_COLS]
                cur.execute(f"INSERT INTO LINKTYPE VALUES ({placeholders})", values)
        if "LINK" in include_tables:
            cur.execute(
                "CREATE TABLE LINK (NO INTEGER, FROMNODENO INTEGER, TONODENO INTEGER, "
                "TSYSSET TEXT, TYPENO INTEGER, NUMLANES INTEGER, V0PRT DOUBLE)"
            )
            cur.executemany(
                "INSERT INTO LINK VALUES (?, ?, ?, ?, ?, ?, ?)", links
            )
        if "LINKPOLY" in include_tables:
            cur.execute(
                'CREATE TABLE LINKPOLY (FROMNODENO INTEGER, TONODENO INTEGER, '
                '"INDEX" INTEGER, XCOORD DOUBLE, YCOORD DOUBLE)'
            )
            cur.executemany(
                "INSERT INTO LINKPOLY VALUES (?, ?, ?, ?, ?)", linkpolys
            )
        for name in extra_tables:
            cur.execute(f'CREATE TABLE "{name}" (NO INTEGER)')
        conn.commit()
    finally:
        conn.close()
    return path
