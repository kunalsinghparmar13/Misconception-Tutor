"""API-level tests for admin protection and safe error handling."""

from __future__ import annotations

import os
from unittest import mock

import pytest
from flask.testing import FlaskClient

from backend.api import app

ADMIN_ROUTES = (
    "/api/security/audit",
    "/api/memory/sessions",
    "/api/llm/dataset",
    "/api/llm/dataset/export",
)


@pytest.fixture
def client() -> FlaskClient:
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_admin_routes_closed_in_production_without_token(client: FlaskClient):
    with mock.patch.dict(os.environ, {"APP_ENV": "production"}):
        os.environ.pop("ADMIN_TOKEN", None)
        for route in ADMIN_ROUTES:
            assert client.get(route).status_code == 403, route


def test_admin_routes_require_the_configured_token(client: FlaskClient):
    with mock.patch.dict(os.environ, {"APP_ENV": "production", "ADMIN_TOKEN": "s3cret"}):
        assert client.get("/api/security/audit").status_code == 403
        wrong = client.get("/api/security/audit", headers={"Authorization": "Bearer nope"})
        assert wrong.status_code == 403
        bearer = client.get("/api/security/audit", headers={"Authorization": "Bearer s3cret"})
        assert bearer.status_code == 200
        header = client.get("/api/security/audit", headers={"X-Admin-Token": "s3cret"})
        assert header.status_code == 200


def test_public_routes_stay_open_in_production(client: FlaskClient):
    with mock.patch.dict(os.environ, {"APP_ENV": "production"}):
        os.environ.pop("ADMIN_TOKEN", None)
        assert client.get("/api/health").status_code == 200


def test_bad_numeric_query_parameter_returns_400_not_500(client: FlaskClient):
    res = client.get("/api/problems/next?difficulty=abc")
    assert res.status_code == 400
    assert res.get_json()["error"] == "Invalid request parameter."


def test_bad_numeric_body_field_returns_400_not_500(client: FlaskClient):
    res = client.post("/api/diagnose", json={"answer": "1/5", "a": "not-a-number"})
    assert res.status_code == 400
