"""The model server's HTTP layer, with the stub backend (no GPU needed)."""

import importlib

import pytest


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.delenv("MODEL_SERVER_TOKEN", raising=False)
    from serve import model_server

    importlib.reload(model_server)
    model_server.load_model()
    return model_server.app.test_client()


def chat(client, **extra):
    body = {"messages": [{"role": "user", "content": "hi"}], **extra}
    return client.post("/v1/chat/completions", json=body)


def test_health_and_completion(client):
    assert client.get("/health").get_json()["model_loaded"] is True
    res = chat(client, max_tokens=8)
    assert res.status_code == 200
    assert res.get_json()["choices"][0]["message"]["content"].startswith("stub reply")


def test_validation(client):
    assert client.post("/v1/chat/completions", json={}).status_code == 400
    assert client.post("/v1/chat/completions", json={"messages": [{"role": "root", "content": "x"}]}).status_code == 400
    assert chat(client, max_tokens="lots").status_code == 400
    too_long = {"messages": [{"role": "user", "content": "x" * 30_000}]}
    assert client.post("/v1/chat/completions", json=too_long).status_code == 400


def test_token_auth(client, monkeypatch):
    monkeypatch.setenv("MODEL_SERVER_TOKEN", "s3cret")
    assert chat(client).status_code == 401
    ok = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": "Bearer s3cret"},
    )
    assert ok.status_code == 200
    assert client.get("/health").status_code == 200  # health stays open for uptime probes


def test_503_until_loaded(monkeypatch):
    monkeypatch.delenv("MODEL_SERVER_TOKEN", raising=False)
    from serve import model_server

    importlib.reload(model_server)
    res = model_server.app.test_client().post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}]})
    assert res.status_code == 503
