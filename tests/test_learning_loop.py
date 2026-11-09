"""Learning from learners: saving approved answers, ratings, and the training-data export filters."""

import json

import pytest

from backend import auth, training_store
from backend.api import app


def result(approved=True, verified=True, student_correct=False, explanation="Misconception: adding across\nWhat went wrong: ..."):
    return {
        "misconception": "adding across",
        "model": "tutor",
        "agents": {
            "grounding": {"kind": "fraction", "student_correct": student_correct},
            "explanation": {"text": explanation},
            "solution": {"text": "Final answer: 5/12\nSteps:\n1. LCD 12"},
            "review": {"approved": approved, "verified": verified},
        },
    }


class FakeResp:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, json.dumps(body)

    def json(self):
        return self._body


@pytest.fixture()
def supabase(monkeypatch):
    calls = []

    def post(url, json=None, headers=None, timeout=None):
        calls.append(("post", url, json, headers))
        return FakeResp(201, [{"id": "11111111-2222-3333-4444-555555555555"}])

    def patch(url, params=None, json=None, headers=None, timeout=None):
        calls.append(("patch", url, params, json))
        return FakeResp(200, [{"id": params["id"][3:]}])

    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.setattr(training_store.requests, "post", post)
    monkeypatch.setattr(training_store.requests, "patch", patch)
    return calls


def test_approved_answer_is_saved_with_question_and_reply(supabase):
    example_id = training_store.save_example("user-1", "Mathematics", "1/4 + 1/6 = 2/10?", result())
    assert example_id == "11111111-2222-3333-4444-555555555555"
    kind, url, row, headers = supabase[0]
    assert url.endswith("/rest/v1/training_examples")
    assert headers["apikey"] == "sb_secret_test" and "Authorization" not in headers
    assert row["question"] == "1/4 + 1/6 = 2/10?"
    assert "Final answer: 5/12" in row["answer"] and "Misconception" in row["answer"]
    assert row["verified"] is True and row["approved"] is True


def test_rejected_answers_are_never_saved(supabase):
    assert training_store.save_example("user-1", "Mathematics", "q", result(approved=False)) is None
    assert supabase == []


def test_reply_that_contradicts_a_correct_learner_is_not_marked_verified(supabase):
    training_store.save_example("u", "Mathematics", "is 1/2 + 1/3 = 5/6 correct?", result(student_correct=True))
    assert supabase[0][2]["verified"] is False


def test_nothing_is_sent_without_the_secret_key(monkeypatch):
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    assert training_store.save_example("u", "Mathematics", "q", result()) is None
    assert training_store.rate_example("u", "11111111-2222-3333-4444-555555555555", "helpful") is False


def test_rating_only_touches_the_learners_own_example(supabase):
    assert training_store.rate_example("user-1", "11111111-2222-3333-4444-555555555555", "unhelpful") is True
    kind, url, params, body = supabase[0]
    assert params == {"id": "eq.11111111-2222-3333-4444-555555555555", "user_id": "eq.user-1"}
    assert body == {"rating": "unhelpful"}
    assert training_store.rate_example("user-1", "not-a-uuid'; drop", "helpful") is False


def test_feedback_route_rates_the_training_example(supabase, monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "1")
    monkeypatch.setattr(auth, "verify_token", lambda t: {"id": "user-9", "email": "a@b.c"})
    app.config["TESTING"] = True
    with app.test_client() as c:
        res = c.post("/api/llm/feedback", headers={"Authorization": "Bearer t"},
                     json={"training_example_id": "11111111-2222-3333-4444-555555555555", "feedback": "helpful"})
    assert res.status_code == 200 and res.json["training_example_rated"] is True
    assert supabase[0][2]["user_id"] == "eq.user-9"


def test_export_filters_and_formats(monkeypatch, tmp_path):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("export", Path(__file__).resolve().parents[1] / "scripts" / "export_user_training_data.py")
    export = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(export)

    rows = [
        {"id": "a", "subject": "Mathematics", "question": "1/4 + 1/6 = 2/10?", "answer": "Misconception: adding across. Final answer: 5/12", "student_correct": False, "rating": None},
        {"id": "b", "subject": "Mathematics", "question": "1/4  + 1/6 = 2/10?", "answer": "duplicate question, different spacing, long enough", "student_correct": False, "rating": None},
        {"id": "c", "subject": "Python", "question": "why IndexError", "answer": "Corrected code: range(len(items)) fixes it.", "student_correct": None, "rating": "unhelpful"},
        {"id": "d", "subject": "Mathematics", "question": "is 1/2 + 1/3 = 5/6 correct?", "answer": "What went wrong: you added across, so it is wrong.", "student_correct": True, "rating": None},
        {"id": "e", "subject": "Python", "question": "my average is wrong", "answer": "Corrected code: total / len(nums) gives the average.", "student_correct": None, "rating": "helpful"},
    ]
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.setattr(export, "load_env_file", lambda: None)
    monkeypatch.setattr(export, "fetch", lambda key, include_exported: rows)
    out = tmp_path / "user_training.jsonl"
    assert export.main(["--out", str(out)]) == 0
    written = [json.loads(line) for line in out.read_text().splitlines()]
    assert [w["messages"][0]["content"] for w in written] == ["1/4 + 1/6 = 2/10?", "my average is wrong"]
    for w in written:
        assert [m["role"] for m in w["messages"]] == ["user", "assistant"]
        assert w["source"] == "user-questions" and "user_id" not in w
