"""On-demand model server (AWS wake Lambda): sleeping/starting states, waking, and retrying a chat."""

import pytest

from tutor_agents import model_client as mc


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class FakeServer:
    """Plays the wake Lambda: asleep until /wake, then 'starting' for a few polls, then ready."""

    def __init__(self, polls_until_ready=2):
        self.awake = False
        self.polls_left = polls_until_ready
        self.wakes = 0
        self.chats = 0

    def get(self, url, headers=None, timeout=None):
        if not self.awake:
            return FakeResponse(503, {"status": "sleeping", "error": "model_sleeping"})
        if self.polls_left > 0:
            self.polls_left -= 1
            return FakeResponse(503, {"status": "starting", "error": "model_starting"})
        return FakeResponse(200, {"status": "ready", "model": "misconception-tutor-gemma4-e4b"})

    def post(self, url, json=None, headers=None, timeout=None):
        if url.endswith("/wake"):
            self.wakes += 1
            self.awake = True
            return FakeResponse(202, {"status": "starting"})
        self.chats += 1
        if not self.awake or self.polls_left > 0:
            return FakeResponse(503, {"status": "starting", "error": "model_starting"})
        return FakeResponse(200, {"choices": [{"message": {"content": "5/12"}}]})


@pytest.fixture()
def server(monkeypatch):
    import requests

    fake = FakeServer()
    monkeypatch.setattr(requests, "get", fake.get)
    monkeypatch.setattr(requests, "post", fake.post)
    monkeypatch.setenv("LLM_BACKEND_URL", "https://wake.example")
    monkeypatch.setenv("LLM_BACKEND_TOKEN", "t")
    monkeypatch.setattr(mc.time, "sleep", lambda s: None)
    return fake


def test_health_reports_a_sleeping_server(server):
    status = mc.ModelClient().health(max_age=0)
    assert status["reachable"] is False
    assert status["state"] == "sleeping"
    assert "asleep" in status["error"]


def test_wait_until_ready_wakes_and_polls(server):
    client = mc.ModelClient()
    seen = []
    assert client.wait_until_ready(timeout=60, interval=0, on_wait=lambda s: seen.append(s["state"])) is True
    assert server.wakes == 1
    assert seen[0] == "sleeping"
    assert client.health(max_age=0)["reachable"] is True


def test_chat_waits_for_a_sleeping_server_then_answers(server):
    result = mc.ModelClient().chat([{"role": "user", "content": "1/4 + 1/6?"}])
    assert result.text == "5/12"
    assert server.wakes == 1
    assert server.chats == 2  # first try hit the sleeping server, second ran after it woke


def test_plain_servers_are_not_treated_as_sleeping(monkeypatch):
    import requests

    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(503, {"error": "Loading model"}))
    monkeypatch.setenv("LLM_BACKEND_URL", "https://tunnel.example")
    client = mc.ModelClient()
    status = client.health(max_age=0)
    assert status["reachable"] is False and "state" not in status
    assert client.wait_until_ready(timeout=1, interval=0) is False


def test_wake_route_without_an_on_demand_server(monkeypatch):
    from backend.api import app

    monkeypatch.setenv("AUTH_REQUIRED", "0")
    app.config["TESTING"] = True
    with app.test_client() as c:
        res = c.post("/api/model/wake")
    assert res.status_code == 200
    assert res.json["status"] in {"unsupported", "ready", "sleeping", "starting"}
