#!/usr/bin/env python
# Eclipse SUMO GIS API fork — see ADR-009
# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

import os
import sys


def _bootstrap_import_path() -> None:
    tools_import = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if tools_import not in sys.path:
        sys.path.insert(0, tools_import)


def main() -> None:
    _bootstrap_import_path()
    import gis._bootstrap  # noqa: F401
    import uvicorn
    from gis.api import create_app

    host = os.environ.get("GIS_API_HOST", "0.0.0.0")
    port = int(os.environ.get("GIS_API_PORT", "8000"))
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
