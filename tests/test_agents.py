"""Tests for the four-agent pipeline using a scripted stand-in for the fine-tuned model."""

import pytest

from tutor_agents import ModelClient, ModelUnavailable, TutorPipeline
from tutor_agents import grounding as gr
from tutor_agents import parsing


EXPLAIN = """Misconception: Adding tops and bottoms directly
What went wrong: You added 1+1 and 4+6 to get 2/10 = 1/5.
Why you made this mistake: Whole-number addition works column by column, so it feels natural to add across.
How to think about it correctly: The bottom number is the slice size; slices must match before you add. 1/4 + 1/6 = 5/12.
Check yourself: What is 1/3 + 1/6?"""

SOLVE_OK = """Final answer: 5/12
Steps:
1. LCM of 4 and 6 is 12.
2. 3/12 + 2/12 = 5/12.
Check: 5/12 is about 0.4167."""

PRACTICE_MATH = """Problem 1
Question: 1/2 + 1/3
Answer: 5/6
Why: Learners add across and get 2/5.

Problem 2
Question: 1/4 + 1/8
Answer: 3/8
Why: Common denominator is 8.

Problem 3
Question: 2/3 + 1/6
Answer: 5/6
Why: Scale 2/3 to 4/6.

Problem 4
Question: 1/5 + 1/10
Answer: 99/100
Why: (deliberately wrong answer - must be dropped)

Problem 5
Question: A recipe uses a cup of flour twice
Answer: 2
Why: word problem, cannot be machine-checked
"""

REVIEW = "Verdict: PASS\nIssues: none\nSuggestion: none"


def scripted(solver_replies, calls=None):
    solver_iter = iter(solver_replies)

    def transport(messages, max_tokens, temperature):
        system = messages[0]["content"]
        if calls is not None:
            calls.append(system[:40])
        if "explain why the learner's answer" in system:
            return EXPLAIN
        if "give the correct answer" in system or "write correct Python code" in system:
            return next(solver_iter)
        if "practice" in system:
            return PRACTICE_MATH
        if "strict reviewer" in system:
            return REVIEW
        raise AssertionError("unexpected agent prompt: " + system[:80])

    return ModelClient(transport=transport)


def test_grounding_detects_fraction_misconception():
    g = gr.ground("Why is 1/4 + 1/6 = 1/5 wrong?", "Mathematics")
    assert g.kind == "fraction"
    assert g.verified_answer == "5/12"
    assert g.student_answer == "1/5"
    assert g.student_correct is False
    assert g.misconception_id == "M1_add_across"


def test_grounding_subtraction_is_not_treated_as_addition():
    g = gr.ground("1/2 - 1/4 = 1/4", "Mathematics")
    assert g.verified_answer == "1/4" and g.student_correct is True


def test_grounding_linear_equation_and_arithmetic():
    eq = gr.ground("Solve 2x + 3 = 11. I got x = 3", "Mathematics")
    assert eq.kind == "equation" and eq.verified_answer == "x = 4" and eq.student_correct is False
    ar = gr.ground("I computed 12 * 7 = 82", "Mathematics")
    assert ar.verified_answer == "84" and ar.student_correct is False


def test_grounding_runs_python_in_sandbox():
    g = gr.ground("print(y)", "Python")
    assert g.kind == "python"
    assert g.code_run and not g.code_run["success"] and g.code_run["error_type"] == "NameError"


def test_safe_evaluator_rejects_code():
    for bad in ("__import__('os').system('echo hi')", "2**9999", "1/0", "abs(-1)"):
        with pytest.raises(gr.UnsafeExpression):
            gr.evaluate(bad)


def test_pipeline_happy_path_math():
    pipe = TutorPipeline(scripted([SOLVE_OK]))
    result = pipe.run("Why is 1/4 + 1/6 = 1/5 wrong?", "Mathematics")
    assert result["explanation"]["misconception"] == "Adding tops and bottoms directly"
    assert result["solution"]["final_answer"] == "5/12"
    assert result["review"]["approved"] is True and result["review"]["verified"] is True
    questions = result["practice_set"]["questions"]
    # the wrong-answer item is dropped, the word problem is kept but flagged unverified
    prompts = [q["prompt"] for q in questions]
    assert "1/5 + 1/10" not in prompts
    assert sum(q["verified"] for q in questions) == 3
    assert any(not q["verified"] for q in questions)
    assert "## Why this went wrong" in result["answer"]


def test_solver_wrong_answer_triggers_one_revision_then_passes():
    events = list(TutorPipeline(scripted(["Final answer: 1/5\nSteps:\n1. add across", SOLVE_OK])).stream(
        "Why is 1/4 + 1/6 = 1/5 wrong?", "Mathematics"))
    assert any(e["event"] == "revision" and e["agent"] == "solver" for e in events)
    done = events[-1]["result"]
    assert done["solution"]["final_answer"] == "5/12"
    assert done["review"]["revisions"] == 1


def test_solver_still_wrong_after_revision_is_flagged_not_hidden():
    wrong = "Final answer: 1/5\nSteps:\n1. add across"
    result = TutorPipeline(scripted([wrong, wrong])).run("Why is 1/4 + 1/6 = 1/5 wrong?", "Mathematics")
    assert result["review"]["approved"] is False
    assert any("5/12" in issue for issue in result["review"]["issues"])


def test_code_path_executes_corrected_code():
    code_solution = "Corrected code:\n```python\nx = 4 + 5\nprint(x)\n```\nWhat changed: removed the undefined name.\nExpected output: 9"
    pipe = TutorPipeline(scripted([code_solution]))
    events = list(pipe.stream("print(y)\nwhy does this fail?", "Python"))
    # practice reply in the scripted model is a maths reply; code practice is parsed leniently -> no code items
    result = events[-1]["result"]
    assert result["solution"]["kind"] == "code"
    assert result["solution"]["run"]["success"] is True
    assert result["solution"]["run"]["stdout"].strip() == "9"
    assert any(c["name"] == "code_runs" and c["status"] == "pass" for c in result["review"]["checks"])


def test_model_unavailable_is_reported_not_faked():
    pipe = TutorPipeline(ModelClient())  # nothing configured
    events = list(pipe.stream("Why is 1/4 + 1/6 = 1/5 wrong?", "Mathematics"))
    assert events[-1]["event"] == "error" and events[-1]["status"] == "model_unavailable"
    with pytest.raises(ModelUnavailable):
        pipe.run("anything", "Mathematics")


def test_parsers_are_tolerant():
    text = "### Problem 1\n**Question:** what is 2/3 + 1/6?\n**Answer:** 5/6\n\n**Problem 2:** 1/2 + 1/2\nAnswer: 1"
    items = parsing.parse_practice(text)
    assert [i["answer"] for i in items] == ["5/6", "1"]
    assert parsing.find_field("**Final answer:** 5/12", ["final answer"]) == "5/12"
    assert parsing.first_python_block("x\n```python\nprint(1)\n```") == "print(1)"
