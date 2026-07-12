"""Tests related to API argument validation"""
import io
from enum import Enum

from fastapi.testclient import TestClient
from vgi_api import app
from devtools import debug

client = TestClient(app)


def test_health():

    response = client.get(
        app.url_path_for("health_check"),
    )

    debug(response.json())

    assert response.status_code == 200
    assert response.json() == "alive"
