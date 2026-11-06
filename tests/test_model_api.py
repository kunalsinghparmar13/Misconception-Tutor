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


def test_remote_llm_backend_forwarding(monkeypatch):
    import requests

    class DummyResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        def json(self):
            return {
                "answer": "### 🎯 Direct Guidance\nHere is your remote Gemma-4B explanation.",
                "model": "Modal-L4-Gemma4B-Tutor",
                "status": "success",
                "metadata": {"topic": "fraction_addition", "misconception": "M1_add_across"},
            }

    monkeypatch.setenv("LLM_BACKEND_URL", "https://modal-gpu-tutor.test.run")
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: DummyResponse())

    client = app.test_client()
    response = client.post(
        "/api/llm/answer",
        json={
            "question": "Why is 1/4 + 1/6 = 1/5 wrong?",
            "subject": "Mathematics",
            "learner_id": "remote_test_student",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert "Direct Guidance" in data["answer"]
    assert data["model"] == "Modal-L4-Gemma4B-Tutor"
    assert "practice_set" in data
    assert data["practice_set"]["count"] == 6


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
