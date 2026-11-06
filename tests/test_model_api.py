from backend.api import app


def test_health_endpoint():
    client = app.test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "online"


def test_ready_endpoint_reports_unloaded_model(monkeypatch):
    from backend import api

    monkeypatch.setattr(
        api.llm_engine,
        "status",
        lambda: {
            "loaded": False,
            "model": "test-adapter",
            "error": "Not loaded",
        },
    )

    client = app.test_client()
    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.get_json()["ready"] is False


def test_unavailable_model_returns_503(monkeypatch):
    from backend import api

    monkeypatch.setattr(
        api.llm_engine,
        "answer_socratic",
        lambda **kwargs: {
            "status": "model_unavailable",
            "answer": "Model unavailable",
        },
    )

    client = app.test_client()

    response = client.post(
        "/api/llm/answer",
        json={
            "question": "Explain why my fraction answer is incorrect.",
            "subject": "Mathematics",
            "learner_id": "test_student",
        },
    )

    assert response.status_code == 503
    assert response.get_json()["status"] == "model_unavailable"


def test_online_training_is_disabled():
    client = app.test_client()

    response = client.post("/api/llm/train")

    assert response.status_code == 410
    assert response.get_json()["status"] == "disabled"


def _serve_stub_model():
    """Run LLM/serve/model_server.py (stub backend) on a free port; return (url, shutdown)."""
    import threading

    from werkzeug.serving import make_server

    from serve import model_server

    model_server._state.update(backend=model_server._StubBackend(), error=None)
    server = make_server("127.0.0.1", 0, model_server.app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_port}", server.shutdown


def test_app_reaches_model_server_over_http(monkeypatch):
    """LLM_BACKEND_URL points at an OpenAI-compatible server; the pipeline talks to it for real."""
    from tutor_agents import ModelClient, TutorPipeline, set_pipeline

    url, shutdown = _serve_stub_model()
    try:
        monkeypatch.setenv("LLM_BACKEND_URL", url)
        client = ModelClient()
        assert client.health()["reachable"] is True
        assert client.chat([{"role": "user", "content": "hi"}], max_tokens=8).text.startswith("stub reply")

        set_pipeline(TutorPipeline(client))
        status = app.test_client().get("/api/backend-status").get_json()
        assert status["llmLoaded"] is True
    finally:
        set_pipeline(None)
        shutdown()


def test_unreachable_model_returns_503_not_canned_text(monkeypatch):
    from tutor_agents import ModelClient, TutorPipeline, set_pipeline

    monkeypatch.setenv("LLM_BACKEND_URL", "http://127.0.0.1:9")  # nothing listens here
    monkeypatch.setenv("LLM_BACKEND_TIMEOUT", "2")
    set_pipeline(TutorPipeline(ModelClient()))
    try:
        res = app.test_client().post(
            "/api/llm/answer",
            json={"question": "Why is 1/4 + 1/6 = 1/5 wrong?", "subject": "Mathematics"},
        )
    finally:
        set_pipeline(None)
    assert res.status_code == 503
    body = res.get_json()
    assert body["status"] == "model_unavailable"
    assert "offline" in body["answer"].lower()


def test_generative_cognitive_socratic_for_python():
    client = app.test_client()
    response = client.post(
        "/api/llm/answer",
        json={
            "question": "def divide(a, b):\n    return a / b\nprint(divide(10, 0))",
            "subject": "Python",
            "learner_id": "py_student",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "ZeroDivisionError" in data["answer"]
    assert "practice_set" in data
    assert len(data["practice_set"]["questions"]) == 6


def test_generative_cognitive_socratic_for_custom_python_index_error():
    client = app.test_client()
    response = client.post(
        "/api/llm/answer",
        json={
            "question": "items = [10, 20]\nprint(items[5])",
            "subject": "Python",
            "learner_id": "custom_py_student",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    # Verifies it parsed the student's exact code rather than the canned 2D grid matrix
    assert "items[5]" in data["answer"] or "IndexError" in data["answer"]
    assert "Off-by-One Horizon" not in data["answer"]


def test_practice_submission_flow():
    client = app.test_client()
    response = client.post(
        "/api/practice/submit",
        json={
            "learner_id": "test_learner_flow",
            "session_id": "sess_123",
            "practice_id": "math_M1_add_across_1",
            "subject": "Mathematics",
            "misconception": "M1_add_across",
            "answer": "5/12",
            "correct_answer": "5/12",
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["correct"] is True
    assert "progress" in payload
