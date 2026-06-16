# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

import os
import sys

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

TOOLS_IMPORT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "tools", "import")
)
if TOOLS_IMPORT not in sys.path:
    sys.path.insert(0, TOOLS_IMPORT)

from gis.api import create_app
import sumolib


def test_health_endpoint():
    client = TestClient(create_app())
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_check_binary_sumo():
    binary = sumolib.checkBinary("sumo")
    assert binary
    assert "sumo" in os.path.basename(binary).lower()
