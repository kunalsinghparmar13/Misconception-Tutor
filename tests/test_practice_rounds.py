"""Practice rounds: distinct problems from the learner's mistake, 80% mastery stop, next round at a new level."""

from backend.api import app
from tutor_agents import ModelClient, TutorPipeline, set_pipeline
from tutor_agents.agents import PracticeItem, _similar, practice_key
from tutor_agents.pipeline import _next_level, round_status

EXPLAIN = """Misconception: Adding tops and bottoms directly
What went wrong: You added 1+1 and 4+6.
Why you made this mistake: Adding across feels natural.
How to think about it correctly: Slices must be the same size. The answer is 5/12.
Check yourself: What is 1/3 + 1/6?"""
SOLVE = "Final answer: 5/12\nSteps:\n1. LCM is 12.\nCheck: 3/12 + 2/12."
ROUND_1 = ("Problem 1\nQuestion: 1/2 + 1/3\nAnswer: 5/6\nWhy: w\n\n"
           "Problem 2\nQuestion: 1/3 + 1/2\nAnswer: 5/6\nWhy: duplicate of problem 1 (same numbers)\n\n"
           "Problem 3\nQuestion: 1/4 + 1/8\nAnswer: 3/8\nWhy: w\n\n"
           "Problem 4\nQuestion: 2/3 + 1/6\nAnswer: 5/6\nWhy: w\n\n"
           "Problem 5\nQuestion: 1/4 + 1/6\nAnswer: 5/12\nWhy: the learner's own problem - must be dropped")
ROUND_2 = ("Problem 1\nQuestion: 1/2 + 1/4\nAnswer: 3/4\nWhy: w\n\n"
           "Problem 2\nQuestion: 1/3 + 1/6\nAnswer: 1/2\nWhy: w\n\n"
           "Problem 3\nQuestion: 1/5 + 1/10\nAnswer: 3/10\nWhy: w")


def make_pipeline(practice_systems):
    replies = iter([ROUND_1, ROUND_2, ROUND_2])

    def transport(messages, max_tokens, temperature):
        system = messages[0]["content"]
        if "explain why the learner's answer" in system:
            return EXPLAIN
        if "give the correct answer" in system:
            return SOLVE
        if "practice problems" in system:
            practice_systems.append(system + "\n" + messages[1]["content"])
            return next(replies, "")
        return "Verdict: PASS\nIssues: none\nSuggestion: none"

    return TutorPipeline(ModelClient(transport=transport), practice_count=3)


def _item(prompt, kind="math", code=None):
    return PracticeItem(id="x", type=kind, prompt=prompt, code=code)


def test_duplicates_are_detected_by_numbers_not_wording():
    assert _similar(practice_key(_item("1/2 + 1/3 = ?")), practice_key(_item("What is 1/3 + 1/2?")))
    assert not _similar(practice_key(_item("1/2 + 1/3")), practice_key(_item("1/2 + 1/5")))
    code_a = practice_key(_item("Fix it", "code", "for i in range(1, 5):\n    print(i)"))
    code_b = practice_key(_item("Fix it", "code", "for i in range(1, 5):\n    print(i) "))
    assert _similar(code_a, code_b)


def test_level_rules():
    assert _next_level("start", 0.3) == "easier"
    assert _next_level("start", 0.6) == "same"
    assert _next_level("harder", 0.2) == "same"
    assert _next_level("easier", 0.1) == "easier"


def test_round_status_mastery_threshold():
    s = {"set_id": "s", "round": 1, "level": "start", "ids": list("abcde"), "results": {}, "answers": {}}
    assert round_status(s)["complete"] is False
    s["results"] = dict(a=True, b=True, c=True, d=True, e=False)  # 80%
    st = round_status(s)
    assert st["complete"] and st["mastered"] and st["next_level"] is None
    s["results"]["d"] = False  # 60%
    st = round_status(s)
    assert not st["mastered"] and st["next_level"] == "same"


def test_full_loop_distinct_problems_then_new_round_then_mastery():
    systems = []
    set_pipeline(make_pipeline(systems))
    client = app.test_client()
    try:
        res = client.post("/api/tutor", json={"question": "1/4 + 1/6 = ? My answer: 2/10", "subject": "Mathematics"})
        ps = res.get_json()["practice_set"]
        prompts = [q["prompt"] for q in ps["questions"]]
        assert prompts == ["1/2 + 1/3", "1/4 + 1/8", "2/3 + 1/6"]  # duplicate and own problem dropped
        assert ps["round"] == 1 and ps["set_id"] and all(q["set_id"] == ps["set_id"] for q in ps["questions"])
        assert "learner's wrong answer: 1/5" in systems[0]  # built from the learner's actual mistake

        # round 1: 1 of 3 right (33%) -> not mastered, next round easier
        answers = ["5/6", "1/2", "1/2"]
        for q, a in zip(ps["questions"], answers):
            info = client.post("/api/practice/submit", json={"practice_id": q["id"], "answer": a}).get_json()["round"]
        assert info["complete"] and not info["mastered"] and info["next_level"] == "easier"
        # a second try does not change the score: the first attempt counts
        again = client.post("/api/practice/submit", json={"practice_id": ps["questions"][1]["id"], "answer": "3/8"}).get_json()
        assert again["round"]["correct"] == 1

        nxt = client.post("/api/practice/next", json={"set_id": ps["set_id"]})
        assert nxt.status_code == 200
        r2 = nxt.get_json()
        assert r2["round"] == 2 and r2["level"] == "easier" and r2["previous"]["correct"] == 1
        assert not set(q["prompt"] for q in r2["questions"]) & set(prompts)
        assert "EASIER" in systems[-1] and "still got these wrong" in systems[-1]

        # round 2: all right -> mastered, no further rounds
        for q in r2["questions"]:
            info = client.post("/api/practice/submit", json={"practice_id": q["id"], "answer": q["correct_answer"]}).get_json()["round"]
        assert info["mastered"] and info["accuracy"] == 1.0
        assert client.post("/api/practice/next", json={"set_id": r2["set_id"]}).status_code == 409
    finally:
        set_pipeline(None)


def test_next_round_requires_finished_round_and_known_set():
    set_pipeline(make_pipeline([]))
    client = app.test_client()
    try:
        ps = client.post("/api/tutor", json={"question": "1/4 + 1/6 = ? My answer: 2/10", "subject": "Mathematics"}).get_json()["practice_set"]
        assert client.post("/api/practice/next", json={"set_id": ps["set_id"]}).status_code == 409
        assert client.post("/api/practice/next", json={"set_id": "nope"}).status_code == 404
    finally:
        set_pipeline(None)
