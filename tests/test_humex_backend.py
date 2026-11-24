"""The Humex backend package (backend/humex): routes, Humo's own model server link, standalone server."""

import pytest
import requests

from backend.api import app
from backend.humex import model as humex_model
from backend.humex.config import load_settings
from tutor_agents import set_pipeline

TUNNEL = "https://humex-model.example.test"


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for name in ("HUMEX_MODEL_URL", "HUMEX_MODEL_TOKEN", "HUMEX_MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)
    humex_model._cached.clear()
    yield
    set_pipeline(None)
    humex_model._cached.clear()


def test_without_a_model_health_says_not_ready():
    data = app.test_client().get("/api/humex/health").get_json()
    assert data["service"] == "humex" and data["ready"] is False and data["dedicated_model"] is False


def test_health_is_public_but_chat_needs_sign_in(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "1")
    client = app.test_client()
    assert client.get("/api/humex/health").status_code == 200
    assert client.post("/api/humex/chat", json={"message": "hi"}).status_code == 401


def test_humo_can_use_its_own_model_server(monkeypatch):
    monkeypatch.setenv("HUMEX_MODEL_URL", TUNNEL + "/")
    monkeypatch.setenv("HUMEX_MODEL_TOKEN", "secret-token")
    client = humex_model.get_client()
    assert client.url == TUNNEL and client.mode == "remote"
    assert client._headers().get("Authorization") == "Bearer secret-token"
    assert humex_model.get_client() is client          # reused, so its health cache is shared
    assert load_settings().dedicated_model


def test_chat_goes_to_humos_server_and_comes_back_reviewed(monkeypatch):
    monkeypatch.setenv("HUMEX_MODEL_URL", TUNNEL)
    sent = []

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.append(url)
        reviewer = json["messages"][0]["content"].startswith("You review a reply")
        text = ("Verdict: PASS\nIssues: none\nBetter reply: same" if reviewer
                else "Good start! What number could both 4 and 6 divide into evenly?")
        return FakeResponse(200, {"choices": [{"message": {"content": text}}]})

    monkeypatch.setattr(requests, "post", fake_post)
    res = app.test_client().post("/api/humex/chat", json={"message": "What is 1/4 + 1/6? I got 2/10"})
    data = res.get_json()
    assert res.status_code == 200 and data["status"] == "ok"
    assert data["review"]["verdict"] == "PASS" and data["reply"].endswith("?")
    assert sent == [TUNNEL + "/v1/chat/completions"] * 2   # coach, then reviewer, both on Humo's server


def test_health_never_leaks_the_model_server_address(monkeypatch):
    monkeypatch.setenv("HUMEX_MODEL_URL", TUNNEL)
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(200, {"status": "ok", "model": "humex-qwen35-4b"}))
    res = app.test_client().get("/api/humex/health")
    assert "example.test" not in res.get_data(as_text=True)
    assert res.get_json()["dedicated_model"] is True


def test_bad_history_shape_is_ignored():
    res = app.test_client().post("/api/humex/chat", json={"message": "", "history": "not a list"})
    assert res.status_code == 400


def test_standalone_server_has_the_same_routes_and_sign_in(monkeypatch):
    from backend.humex.server import create_app

    monkeypatch.setenv("AUTH_REQUIRED", "1")
    client = create_app().test_client()
    assert client.get("/api/humex/health").get_json()["service"] == "humex"
    assert client.post("/api/humex/chat", json={"message": "hi"}).status_code == 401
