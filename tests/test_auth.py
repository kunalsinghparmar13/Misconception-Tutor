"""Sign-in: tutor routes need a Supabase session; pages and health checks stay public."""

import pytest

from backend import auth
from backend.api import app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "1")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_public_pages_and_config_need_no_sign_in(client):
    assert client.get("/login").status_code == 200
    assert b"Create account" in client.get("/login").data
    cfg = client.get("/config.js")
    assert cfg.status_code == 200
    assert b"window.SUPABASE_CONFIG" in cfg.data
    assert b"sb_publishable_" in cfg.data
    assert client.get("/api/health").status_code == 200
    assert client.get("/logo.png").status_code == 200


def test_tutor_routes_refuse_requests_without_a_session(client, monkeypatch):
    monkeypatch.setattr(auth, "verify_token", lambda token: pytest.fail("no token should not be verified"))
    for path in ("/api/tutor/stream", "/api/practice/submit", "/api/practice/next", "/api/llm/feedback"):
        res = client.post(path, json={})
        assert res.status_code == 401, path
        assert res.json["status"] == "unauthenticated"


def test_invalid_token_is_refused(client, monkeypatch):
    monkeypatch.setattr(auth, "verify_token", lambda token: None)
    res = client.post("/api/practice/submit", json={}, headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_valid_session_reaches_the_route(client, monkeypatch):
    seen = {}

    def fake_verify(token):
        seen["token"] = token
        return {"id": "11111111-1111-1111-1111-111111111111", "email": "learner@example.com"}

    monkeypatch.setattr(auth, "verify_token", fake_verify)
    res = client.post("/api/practice/submit", json={}, headers={"Authorization": "Bearer good-token"})
    assert seen["token"] == "good-token"
    assert res.status_code == 400  # past the sign-in check; the empty body is the route's own validation error


def test_sign_in_check_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "0")
    app.config["TESTING"] = True
    with app.test_client() as c:
        assert c.post("/api/practice/submit", json={}).status_code == 400


def test_verify_token_caches_answers(monkeypatch):
    calls = []

    class Res:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "abc", "email": "a@example.com"}

    def fake_get(url, headers, timeout):
        calls.append(headers["Authorization"])
        return Res()

    monkeypatch.setattr(auth.requests, "get", fake_get)
    auth._cache.clear()
    assert auth.verify_token("t1") == {"id": "abc", "email": "a@example.com"}
    assert auth.verify_token("t1") == {"id": "abc", "email": "a@example.com"}
    assert calls == ["Bearer t1"]
