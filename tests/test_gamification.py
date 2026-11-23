"""Unit tests for Sikora AI Gamification Suite: XP, Levels, Streaks, Daily Challenges, and Explain-It-Back."""

from __future__ import annotations

import sqlite3
import pytest
import uuid

from backend import gamification
from backend.api import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def mem_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    gamification.init_gamification_tables(conn)
    yield conn
    conn.close()


def test_level_for_xp_math():
    """Verifies that XP maps to proper RPG-style tiers and titles."""
    l1 = gamification.level_for_xp(0)
    assert l1["level"] == 1
    assert l1["title"] == "Curious Beginner"
    assert l1["xp_to_next_level"] == 200

    l10 = gamification.level_for_xp(800)
    assert l10["level"] >= 10
    assert l10["title"] == "Pattern Spotter"

    l_max = gamification.level_for_xp(25000)
    assert l_max["level"] == 50
    assert l_max["title"] == "Cognitive Master"


def test_award_xp_and_combos(mem_db):
    """Verifies XP award, combo bonuses on 3 consecutive correct answers, and logging."""
    # Action 1: Question asked
    r1 = gamification.award_xp(mem_db, "test_user", "ask_question")
    assert r1["xp_earned"] == 10
    assert r1["total_xp"] == 10

    # Practice corrects (combo test)
    r2 = gamification.award_xp(mem_db, "test_user", "practice_correct", is_correct=True)
    assert r2["combo_count"] == 1
    assert r2["combo_bonus"] is False

    r3 = gamification.award_xp(mem_db, "test_user", "practice_correct", is_correct=True)
    assert r3["combo_count"] == 2

    # 3rd consecutive correct triggers combo bonus!
    r4 = gamification.award_xp(mem_db, "test_user", "practice_correct", is_correct=True)
    assert r4["combo_count"] == 3
    assert r4["combo_bonus"] is True
    assert r4["bonus_xp"] == gamification.COMBO_BONUS_XP


def test_streak_recording(mem_db):
    """Verifies active day recording and streak retrieval."""
    res = gamification.record_active_day(mem_db, "student_1")
    assert res["current_streak"] == 1
    assert res["total_active_days"] == 1
    assert res["freezes_available"] >= 1

    # Calling again today doesn't double-increment
    res2 = gamification.record_active_day(mem_db, "student_1")
    assert res2["current_streak"] == 1

    profile = gamification.get_streak(mem_db, "student_1")
    assert profile["current_streak"] == 1
    assert len(profile["week_days"]) == 7


def test_evaluate_explanation_rubric():
    """Verifies 1-star, 2-star, and 3-star evaluations for student's active recall."""
    # Too brief
    e1 = gamification.evaluate_explanation("M1_add_across", "I don't know")
    assert e1["stars"] == 1
    assert "brief" in e1["feedback"].lower()

    # Moderate explanation
    e2 = gamification.evaluate_explanation(
        "M1_add_across",
        "We need to find the common denominator first instead of adding.",
        subject="Mathematics"
    )
    assert e2["stars"] >= 2

    # Deep explanation with why, how, and multiple key terms
    e3 = gamification.evaluate_explanation(
        "M1_add_across",
        "You cannot add the numerators directly because the fraction slices are different sizes. First you must find the common denominator using the LCM, scale both fractions, and then add.",
        subject="Mathematics"
    )
    assert e3["stars"] == 3
    assert "outstanding" in e3["feedback"].lower()


def test_gamification_api_routes(client):
    """Verifies full Flask API endpoints for gamification profile, daily challenge, and explain-it-back."""
    gamer_id = f"gamer_{uuid.uuid4().hex[:6]}"

    # 1. Profile
    res = client.get(f"/api/gamification/profile?learner_id={gamer_id}")
    assert res.status_code == 200
    data = res.get_json()
    assert "xp" in data
    assert "streak" in data
    assert "daily_challenge" in data

    # 2. Daily Challenge fetch
    dc_res = client.get(f"/api/daily-challenge?learner_id={gamer_id}")
    assert dc_res.status_code == 200
    dc = dc_res.get_json()
    assert "target_misc" in dc

    # 3. Daily Challenge submit
    sub_res = client.post("/api/daily-challenge/submit", json={
        "learner_id": gamer_id,
        "answer": "5/12",
        "expected_answer": "5/12",
        "target_misc": "M1_add_across",
    })
    assert sub_res.status_code == 200
    sub_data = sub_res.get_json()
    assert sub_data["correct"] is True
    assert sub_data["completed"] is True
    assert sub_data["xp_earned"] > 0

    # 4. Explain-It-Back submit
    exp_res = client.post("/api/explain-back", json={
        "learner_id": gamer_id,
        "misconception": "Adding across fractions",
        "explanation": "Because fractions represent proportional parts of a whole, they must share a common denominator before their numerators can be combined.",
        "subject": "Mathematics",
    })
    assert exp_res.status_code == 200
    exp_data = exp_res.get_json()
    assert exp_data["stars"] in (2, 3)
    assert "feedback" in exp_data
    assert exp_data["xp_earned"] > 0

    # 5. Explain-It-Back history
    hist_res = client.get(f"/api/explain-back/history?learner_id={gamer_id}")
    assert hist_res.status_code == 200
    hist = hist_res.get_json()
    assert hist["count"] >= 1
