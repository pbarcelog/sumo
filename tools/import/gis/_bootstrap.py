# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

import os
import sys


def configure_paths() -> None:
    """Ensure `tools/` and `tools/import/` are on sys.path for sumolib and gis."""
    gis_root = os.path.dirname(os.path.abspath(__file__))
    tools_import = os.path.dirname(gis_root)
    tools_dir = os.path.dirname(tools_import)
    for path in (tools_import, tools_dir):
        if path not in sys.path:
            sys.path.insert(0, path)


configure_paths()
