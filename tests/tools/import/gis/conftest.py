# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
TOOLS_IMPORT = os.path.join(TOOLS, "import")
for path in (TOOLS, TOOLS_IMPORT):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("SUMO_HOME", ROOT)
os.environ.setdefault("GIS_API_WORKSPACE", os.path.join(ROOT, "tests", "tools", "import", "gis", "_workspace"))
