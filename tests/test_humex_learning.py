"""Humo learns from real conversations in scheduled training rounds: what is saved, rated and exported."""

import json
import threading

import pytest

from backend import auth, training_store
from backend.api import app
from tutor_agents import ModelClient, TutorPipeline, set_pipeline
from tutor_agents.humex import coach_system_prompt, training_messages

GOOD = "Not quite. It looks like you added the tops together and the bottoms together. What must the bottoms be?"


def good_result(**over):
    base = {"reply": GOOD, "verdict": "PASS", "focus": "wrong", "hint_level": 1, "kind": "fraction", "coding": False,
            "model": "humex-qwen35-4b", "checks": [{"name": "no_answer_leak", "ok": True},
                                                   {"name": "no_answer_phrase", "ok": True},
                                                   {"name": "no_full_code", "ok": True}]}
    return {**base, **over}


# ---------------------------------------------------------------- what is worth learning from

def test_only_checked_model_replies_are_learnable():
    assert training_store.humex_turn_is_learnable(good_result())
    assert training_store.humex_turn_is_learnable(good_result(verdict="REVISED"))
    assert not training_store.humex_turn_is_learnable(good_result(verdict="FALLBACK"))   # built-in safety text
    leaked = good_result(checks=[{"name": "no_answer_leak", "ok": False}])
    assert not training_store.humex_turn_is_learnable(leaked)


def test_record_fits_the_column_and_keeps_the_latest_turns():
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"turn {i} " + "x" * 1100} for i in range(10)]
    text = training_store.humex_record("What next?", history, good_result(), "en", False)
    record = json.loads(text)
    assert len(text) <= 4000 and record["message"] == "What next?"
    assert record["history"][-1]["content"].startswith("turn 9")


# ---------------------------------------------------------------- the chat route saves without slowing the reply

@pytest.fixture()
def signed_in(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "1")
    monkeypatch.setattr(auth, "verify_token", lambda token: {"id": "11111111-1111-1111-1111-111111111111"})
    monkeypatch.setattr(training_store, "enabled", lambda: True)
    saved, done = [], threading.Event()

    def fake_save(*args):
        saved.append(args)
        done.set()

    monkeypatch.setattr(training_store, "save_humex_turn", fake_save)
    client = ModelClient(transport=lambda m, t, temp: ("Verdict: PASS\nIssues: none\nBetter reply: same"
                                                        if m[0]["content"].startswith("You review a reply") else
                                                        "What could both 4 and 6 divide into?"))
    set_pipeline(TutorPipeline(client))
    yield saved, done
    set_pipeline(None)


def test_signed_in_turn_is_saved_in_the_background(signed_in):
    saved, done = signed_in
    res = app.test_client().post("/api/humex/chat", json={"message": "What is 1/4 + 1/6? I got 2/10"},
                                 headers={"Authorization": "Bearer token"})
    data = res.get_json()
    assert res.status_code == 200 and data["example_id"]
    assert done.wait(5)
    user_id, message, _history, reply, _lang, _coding, example_id = saved[0]
    assert example_id == data["example_id"] and message.startswith("What is 1/4")
    assert "added the tops" in reply["reply"]


def test_not_signed_in_nothing_is_saved(monkeypatch):
    monkeypatch.setattr(training_store, "enabled", lambda: True)
    called = []
    monkeypatch.setattr(training_store, "save_humex_turn", lambda *a: called.append(a))
    set_pipeline(TutorPipeline(ModelClient(transport=lambda m, t, temp: "What do you notice?")))
    try:
        data = app.test_client().post("/api/humex/chat", json={"message": "How do I add 1/3 and 1/4?"}).get_json()
    finally:
        set_pipeline(None)
    assert data.get("example_id") is None and called == []


def test_feedback_is_recorded_for_the_learners_own_turn(signed_in, monkeypatch):
    rated = []
    monkeypatch.setattr(training_store, "rate_example", lambda user, eid, rating: rated.append((user, eid, rating)) or True)
    res = app.test_client().post("/api/humex/feedback", json={"example_id": "abc-123", "rating": "unhelpful"},
                                 headers={"Authorization": "Bearer token"})
    assert res.get_json() == {"saved": True}
    assert rated == [("11111111-1111-1111-1111-111111111111", "abc-123", "unhelpful")]


def test_feedback_needs_a_valid_rating():
    assert app.test_client().post("/api/humex/feedback", json={"example_id": "x", "rating": "meh"}).status_code == 400


# ---------------------------------------------------------------- export: the exact prompt Humo runs with

def test_exported_turn_uses_humos_runtime_prompt():
    from scripts.export_user_training_data import keep, to_training_row
    record = json.loads(training_store.humex_record(
        "What is 1/4 + 1/6? I got 2/10", [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hello! What shall we try?"}],
        good_result(), "en", False))
    row = {"subject": "humex", "question": json.dumps(record), "answer": GOOD, "student_correct": False}
    assert keep(row) == (True, "")
    messages = to_training_row(row)["messages"]
    assert messages[0] == {"role": "system", "content": coach_system_prompt("wrong", 1, "en", False)}
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user", "assistant"]
    assert messages[-1]["content"] == GOOD


@pytest.mark.parametrize("question, answer, why", [
    ("not json", GOOD, "unreadable humex record"),
    (json.dumps({"humex": 1, "message": "hi"}), "Here is how it works, step by step.", "humex reply asks no question"),
])
def test_export_skips_bad_humex_rows(question, answer, why):
    from scripts.export_user_training_data import keep
    assert keep({"subject": "humex", "question": question, "answer": answer}) == (False, why)


def test_training_messages_match_the_saved_record():
    record = {"humex": 1, "message": "Is there another way?", "history": [], "focus": "another_way", "hint_level": 2,
              "language": "en", "coding": True}
    msgs = training_messages(record, "Here's a different way: use a dictionary. What would the keys be?")
    assert "programming question" in msgs[0]["content"] and msgs[1]["content"] == "Is there another way?"
