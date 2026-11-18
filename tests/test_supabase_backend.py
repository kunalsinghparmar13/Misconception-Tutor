"""Tests for Supabase Cloud Data Persistence, BKT Synchronization, and Fallback."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from backend import auth, backend_code, supabase_db
from backend.api import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_supabase_configured():
    """Verifies config detection when URL and publishable key exist."""
    assert supabase_db.is_configured() is True


def test_build_headers_with_user_token():
    """Ensures user's JWT is passed in Authorization header for RLS evaluation."""
    headers = supabase_db._build_headers(auth_token="jwt-token-123", prefer_merge=True)
    assert headers["Authorization"] == "Bearer jwt-token-123"
    assert "return=representation" in headers["Prefer"]
    assert "resolution=merge-duplicates" in headers["Prefer"]


def test_sync_tutor_session_mock():
    """Verifies tutor session serialization and PostgREST payload."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = [{"id": "sess_test_123"}]

    with patch("requests.post", return_value=mock_resp) as mock_post:
        res = supabase_db.sync_tutor_session({
            "id": "sess_test_123",
            "learner_id": "user_abc",
            "question": "Why is 1/2 + 1/3 not 2/5?",
            "subject": "Mathematics",
            "misconception": "Adding numerators and denominators directly",
            "result": {"explanation": "Find common denominator."},
        }, auth_token="fake_token")

        assert res == "sess_test_123"
        assert mock_post.called
        call_url = mock_post.call_args[0][0]
        assert call_url.endswith("/rest/v1/tutor_sessions")
        payload = mock_post.call_args[1]["json"]
        assert payload["id"] == "sess_test_123"
        assert payload["learner_id"] == "user_abc"


def test_fetch_tutor_sessions_mock():
    """Verifies fetching learner sessions with search and subject filters."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "id": "sess_01",
            "learner_id": "user_abc",
            "question": "What is recursion?",
            "subject": "Python",
            "misconception": "Base case omission",
            "created_at": "2026-11-18T10:00:00Z",
        }
    ]

    with patch("requests.get", return_value=mock_resp):
        sessions = supabase_db.fetch_tutor_sessions("user_abc", limit=10, subject="Python")
        assert len(sessions) == 1
        assert sessions[0]["id"] == "sess_01"
        assert sessions[0]["subject"] == "Python"


def test_sync_and_fetch_bkt_state_mock():
    """Verifies BKT knowledge state upsert and fetch."""
    post_resp = MagicMock()
    post_resp.status_code = 201
    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = [{"misc_id": "M1_add_across", "p_mastery": 0.85}]

    with patch("requests.post", return_value=post_resp):
        saved = supabase_db.sync_bkt_state("user_abc", "M1_add_across", 0.85, auth_token="tok")
        assert saved is True

    with patch("requests.get", return_value=get_resp):
        masteries = supabase_db.fetch_bkt_masteries("user_abc", auth_token="tok")
        assert masteries == {"M1_add_across": 0.85}


def test_practice_attempt_mock():
    """Verifies practice attempt logging in Supabase."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201

    with patch("requests.post", return_value=mock_resp) as mock_post:
        logged = supabase_db.sync_practice_attempt({
            "learner_id": "user_abc",
            "practice_id": "prac_42",
            "subject": "Mathematics",
            "misconception": "M1_add_across",
            "correct": True,
            "answer": "5/12",
        }, auth_token="tok")
        assert logged is True
        assert mock_post.called


def test_notifications_mock():
    """Verifies notification retrieval and read status marking."""
    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = [
        {
            "id": "notif_01",
            "title": "Practice Reminder",
            "message": "Time to practice fractions!",
            "icon": "zap",
            "category": "practice",
            "read_status": False,
            "created_at": "2026-11-18T10:00:00Z",
        }
    ]
    patch_resp = MagicMock()
    patch_resp.status_code = 204

    with patch("requests.get", return_value=get_resp):
        notifs = supabase_db.fetch_learner_notifications("user_abc", auth_token="tok")
        assert len(notifs) == 1
        assert notifs[0]["id"] == "notif_01"
        assert notifs[0]["read"] is False

    with patch("requests.patch", return_value=patch_resp):
        ok = supabase_db.mark_notification_read("notif_01", learner_id="user_abc", auth_token="tok")
        assert ok is True


def test_offline_fallback_resilience(client):
    """Verifies that network exceptions fall back gracefully to local SQLite without 500 errors."""
    with patch("requests.get", side_effect=Exception("Network unreachable")), \
         patch("requests.post", side_effect=Exception("Network unreachable")):

        # Library sessions list still works (serves local SQLite demo data)
        res = client.get("/api/learner/sessions?learner_id=student_demo")
        assert res.status_code == 200
        assert len(res.get_json()["sessions"]) >= 3

        # Dashboard still works
        dash_res = client.get("/api/learner/dashboard?learner_id=student_demo")
        assert dash_res.status_code == 200
        assert "weekly_goal" in dash_res.get_json()

        # Notifications still work
        notif_res = client.get("/api/notifications?learner_id=student_demo")
        assert notif_res.status_code == 200
        assert len(notif_res.get_json()["notifications"]) >= 1
