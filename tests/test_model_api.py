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