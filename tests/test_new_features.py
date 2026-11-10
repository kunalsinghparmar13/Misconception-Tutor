"""Unit tests for the new high-class backend endpoints:
Sessions Library, Practice Lab, Analytics Dashboard, Notifications, and Context Attachment.
"""

from __future__ import annotations

import io
import json
import pytest

from backend import api, auth, backend_code


@pytest.fixture
def client():
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        yield c


def test_learner_sessions_crud(client):
    """Verifies listing, creating, retrieving, and deleting library study sessions."""
    # List sessions (should have seed data)
    res = client.get("/api/learner/sessions?learner_id=test_student")
    assert res.status_code == 200
    data = res.get_json()
    assert "sessions" in data
    assert len(data["sessions"]) >= 3

    # Create new session
    payload = {
        "learner_id": "test_student",
        "question": "How do I invert a binary tree in Python?",
        "subject": "Python",
        "misconception": "In-place mutation vs returning root",
        "result": {
            "explain": "Swap left and right children recursively.",
            "solve": "root.left, root.right = invert(root.right), invert(root.left)",
        }
    }
    create_res = client.post("/api/learner/sessions", json=payload)
    assert create_res.status_code == 201
    created = create_res.get_json()
    assert created["success"] is True
    sid = created["id"]

    # Retrieve single session
    get_res = client.get(f"/api/learner/sessions/{sid}")
    assert get_res.status_code == 200
    sess_data = get_res.get_json()
    assert sess_data["question"] == payload["question"]
    assert sess_data["result"]["explain"] == payload["result"]["explain"]

    # Delete session
    del_res = client.delete(f"/api/learner/sessions/{sid}?learner_id=test_student")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True


def test_practice_catalog_and_generation(client):
    """Verifies practice lab catalog, problem generation, and answer verification."""
    # Catalog
    res = client.get("/api/practice/catalog")
    assert res.status_code == 200
    modules = res.get_json()["modules"]
    assert len(modules) >= 6

    # Generate question
    gen_res = client.post("/api/practice/generate", json={"topic_id": "math_quadratic"})
    assert gen_res.status_code == 200
    prob = gen_res.get_json()["problem"]
    assert "prompt" in prob
    assert prob["topic_id"] == "math_quadratic"

    # Verify correct answer
    verify_res = client.post("/api/practice/verify", json={
        "problem_id": prob["id"],
        "user_answer": prob["expected_answer"],
        "expected_answer": prob["expected_answer"],
        "topic_id": "math_quadratic",
        "subject": "Mathematics",
    })
    assert verify_res.status_code == 200
    v_data = verify_res.get_json()
    assert v_data["correct"] is True
    assert "mastery_increase" in v_data


def test_learner_dashboard_data(client):
    """Verifies learner analytics, weekly goal, active streak, and BKT concept masteries."""
    res = client.get("/api/learner/dashboard?learner_id=test_student")
    assert res.status_code == 200
    data = res.get_json()
    assert "weekly_goal" in data
    assert "streak" in data
    assert "concept_mastery" in data
    assert len(data["concept_mastery"]) >= 5


def test_notifications_route(client):
    """Verifies notification listing and mark-as-read."""
    res = client.get("/api/notifications?learner_id=test_student")
    assert res.status_code == 200
    data = res.get_json()
    assert "notifications" in data
    assert len(data["notifications"]) >= 1

    read_res = client.post("/api/notifications/read", json={"id": "all"})
    assert read_res.status_code == 200
    assert read_res.get_json()["success"] is True


def test_context_upload(client):
    """Verifies file attachment and prompt formatting."""
    # Test file upload via multipart
    data = {
        "file": (io.BytesIO(b"def solve(x):\n    return x * 2\n"), "solver.py")
    }
    res = client.post("/api/context/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data["filename"] == "solver.py"
    assert res_data["language"] == "python"
    assert "Attached File: solver.py" in res_data["formatted_prompt"]
