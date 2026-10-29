"""
================================================================================
Misconception Tutor: End-to-End Test Suite
Tests arithmetic parser, cognitive buggy rules, 3 strict problem invariants,
Bayesian Knowledge Tracing, continuous LLM dataset logging, fine-tuning orchestrator,
and all Flask API endpoints.
================================================================================
"""

import json
from fractions import Fraction
import pytest
from backend import backend_code
from backend.api import app
from backend.llm_engine import llm_engine
from backend.trainer import continuous_trainer


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ==============================================================================
# 1. RATIONAL ARITHMETIC & PARSER TESTS
# ==============================================================================

def test_parse_fraction_formats():
    assert backend_code.parse_fraction("5/12") == Fraction(5, 12)
    assert backend_code.parse_fraction("  2 / 10  ") == Fraction(1, 5)
    assert backend_code.parse_fraction("2") == Fraction(2, 1)
    assert backend_code.parse_fraction("-1") == Fraction(-1, 1)
    assert backend_code.parse_fraction("1 1/2") == Fraction(3, 2)
    assert backend_code.parse_fraction("2 3/4") == Fraction(11, 4)
    assert backend_code.parse_fraction("0.5") == Fraction(1, 2)
    assert backend_code.parse_fraction("1.25") == Fraction(5, 4)


def test_parse_fraction_invalid():
    assert backend_code.parse_fraction("1/0") is None
    assert backend_code.parse_fraction("abc") is None
    assert backend_code.parse_fraction("") is None
    assert backend_code.parse_fraction("  ") is None


def test_check_answer_equivalence():
    is_corr, frac = backend_code.check_answer("10/24", "5/12")
    assert is_corr is True
    assert frac == Fraction(5, 12)

    is_corr, _ = backend_code.check_answer("1/5", "5/12")
    assert is_corr is False


# ==============================================================================
# 2. COGNITIVE BUGGY RULES (M1-M5)
# ==============================================================================

def test_buggy_rules_addition():
    # 1/4 + 1/6
    a, b, c, d = 1, 4, 1, 6
    # M1: Add across -> 2/10 = 1/5
    assert backend_code.BUGS_ADD["M1_add_across"](a, b, c, d) == (2, 10)
    # M2: Tops add, bottoms multiply -> 2/24 = 1/12
    assert backend_code.BUGS_ADD["M2_tops_add_bottoms_multiply"](a, b, c, d) == (2, 24)
    # M3: Unscaled numerators -> 2/12 = 1/6
    assert backend_code.BUGS_ADD["M3_no_scaling"](a, b, c, d) == (2, 12)


def test_buggy_rules_division():
    # 1/2 ÷ 1/4
    a, b, c, d = 1, 2, 1, 4
    # M4: Multiply straight across -> 1/8
    assert backend_code.BUGS_DIV["M4_divide_multiply_across"](a, b, c, d) == (1, 8)
    # M5: Flips dividend (first fraction) -> 2/4 = 1/2
    assert backend_code.BUGS_DIV["M5_flip_wrong_fraction"](a, b, c, d) == (2, 4)


# ==============================================================================
# 3. BASE PROBLEM BANK & GENERATOR INVARIANTS (3 STRICT CHECKS)
# ==============================================================================

def test_base_problem_bank_count():
    assert len(backend_code.BASE_PROBLEMS) == 30
    add_probs = [p for p in backend_code.BASE_PROBLEMS if p["type"] == "fraction_add"]
    div_probs = [p for p in backend_code.BASE_PROBLEMS if p["type"] == "fraction_div"]
    assert len(add_probs) == 20
    assert len(div_probs) == 10


def test_targeted_problem_generator_invariants():
    for target in ["M1_add_across", "M2_tops_add_bottoms_multiply", "M3_no_scaling"]:
        prob = backend_code.generate_targeted_problem(target, difficulty=1)
        corr = backend_code.parse_fraction(prob["correct_answer"])
        mine = backend_code.parse_fraction(prob["bug_answers"][target])
        others = [backend_code.parse_fraction(v) for m, v in prob["bug_answers"].items() if m != target]

        # 3 Strict Checks:
        # Check 1: Target bug answer != correct answer
        assert mine != corr, f"Check 1 failed on {target}: bug answer equals correct answer!"
        # Check 2: Target bug answer != other bug answers (zero collision)
        assert mine not in others, f"Check 2 failed on {target}: collision with another bug!"
        # Check 3: Arithmetic verified
        assert corr == backend_code.correct_add(prob["a"], prob["b"], prob["c"], prob["d"])


# ==============================================================================
# 4. STEP-BY-STEP COGNITIVE REPLAY & EXPLANATIONS
# ==============================================================================

def test_cognitive_replay_generation():
    replay_m1 = backend_code.generate_replay("M1_add_across", 1, 4, 1, 6)
    assert "added tops (1+1=2) and bottoms (4+6=10)" in replay_m1
    assert "matches your answer" in replay_m1

    replay_m4 = backend_code.generate_replay("M4_divide_multiply_across", 1, 2, 1, 4)
    assert "multiplied across without flipping" in replay_m4


# ==============================================================================
# 5. BAYESIAN KNOWLEDGE TRACING (BKT) & SQLITE LOGGING
# ==============================================================================

def test_bkt_mastery_progression():
    import time
    learner_id = f"test_learner_bkt_{int(time.time() * 1000)}"
    # Prior mastery
    p_init = backend_code.DEFAULT_BKT_PARAMS["p_init"]

    # Student makes error on M1
    backend_code.log_attempt_db(learner_id, "s1", "prob1", "M1_add_across", "1/5", 0, "M1_add_across", 0.95)
    m1 = backend_code.get_learner_mastery(learner_id)["M1_add_across"]
    # Error should decrease concept mastery below prior
    assert m1 < p_init, f"Expected mastery drop on error, got {m1}"

    # Student receives remediation and answers correctly
    backend_code.log_attempt_db(learner_id, "s1", "prob2", "M1_add_across", "5/12", 1, None, 1.0)
    m2 = backend_code.get_learner_mastery(learner_id)["M1_add_across"]
    # Success should increase mastery
    assert m2 > m1, f"Expected mastery increase on correct answer, got {m2} <= {m1}"


# ==============================================================================
# 6. LLM ENGINE & SOCRATIC TUTOR
# ==============================================================================

def test_llm_socratic_response_format():
    res = llm_engine.answer_socratic(
        subject="Mathematics",
        question="I am factoring 2x² + 5x - 12 = 0. My signs feel wrong.",
        mode="diagnostic",
        learner_id="test_student",
    )
    assert res["status"] == "success"
    assert "First Divergence" in res["answer"]
    assert "Key Takeaway" in res["answer"]
    assert res["sample_id"].startswith("samp_")


def test_training_sample_logging_and_feedback():
    sample_id = llm_engine.log_training_sample(
        subject="Mathematics",
        instruction="Diagnose student error on fraction addition.",
        user_input="1/4 + 1/6 = 1/5",
        model_output="Misconception: Add Across M1.",
        learner_id="test_feedback_user",
        misconception="M1_add_across",
    )
    assert sample_id is not None
    # Update feedback
    updated = llm_engine.update_sample_feedback(sample_id, "helpful", "Accurate diagnosis")
    assert updated is True


# ==============================================================================
# 7. CONTINUOUS FINE-TUNING ORCHESTRATOR
# ==============================================================================

def test_continuous_trainer_status():
    status = continuous_trainer.get_status()
    assert "activeCheckpoint" in status
    assert "latestLoss" in status
    assert status["globalStep"] >= 923


# ==============================================================================
# 8. FLASK API ENDPOINTS INTEGRATION
# ==============================================================================

def test_api_static_routes(client):
    r_index = client.get("/")
    assert r_index.status_code == 200
    assert b"Where are you stuck today?" in r_index.data

    r_app = client.get("/app.js")
    assert r_app.status_code == 200
    assert b"showResponse" in r_app.data


def test_api_health_and_status(client):
    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    assert r_health.json["status"] == "online"

    r_status = client.get("/api/backend-status")
    assert r_status.status_code == 200
    assert r_status.json["liveAiEnabled"] is True


def test_api_problem_routes(client):
    r_base = client.get("/api/problems/base")
    assert r_base.status_code == 200
    assert len(r_base.json["problems"]) == 30

    r_next = client.get("/api/problems/next?learner_id=test_user&operation=fraction_add&difficulty=1")
    assert r_next.status_code == 200
    assert "problem" in r_next.json
    assert "text" in r_next.json["problem"]


def test_api_diagnose_endpoint(client):
    # Test incorrect answer that triggers M1
    r_diag = client.post("/api/diagnose", json={
        "learner_id": "test_api_learner",
        "session_id": "sess_01",
        "answer": "1/5",
        "correct_answer": "5/12",
        "target_misc": "M1_add_across",
        "problem_text": "1/4 + 1/6 = ?",
        "operation": "fraction_add",
        "a": 1, "b": 4, "c": 1, "d": 6,
    })
    assert r_diag.status_code == 200
    data = r_diag.json
    assert data["correct"] is False
    assert data["detected_misc"] == "M1_add_across"
    assert "added tops" in data["cognitive_replay"]
    assert data["follow_up_problem"] is not None
    assert "training_sample_id" in data


def test_api_learner_profile_and_teacher_analytics(client):
    r_profile = client.get("/api/learner/profile?learner_id=test_api_learner")
    assert r_profile.status_code == 200
    assert "masteries" in r_profile.json
    assert "M1_add_across" in r_profile.json["masteries"]

    r_analytics = client.get("/api/teacher/analytics")
    assert r_analytics.status_code == 200
    assert "heatmap" in r_analytics.json


def test_api_dataset_and_export(client):
    r_dataset = client.get("/api/llm/dataset")
    assert r_dataset.status_code == 200
    assert r_dataset.json["total_samples"] > 0

    r_export_jsonl = client.get("/api/llm/dataset/export?format=jsonl")
    assert r_export_jsonl.status_code == 200
    assert "application/x-jsonlines" in r_export_jsonl.content_type

    r_export_csv = client.get("/api/llm/dataset/export?format=csv")
    assert r_export_csv.status_code == 200
    assert "text/csv" in r_export_csv.content_type
