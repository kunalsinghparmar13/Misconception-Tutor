"""
================================================================================
Test Suite: Python Code Compiler, AST Debugger & General Problem Solver
================================================================================
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient

from backend.api import app
from backend.general_solver import general_solver
from backend.python_debugger import python_debugger


@pytest.fixture
def client() -> FlaskClient:
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ==============================================================================
# TEST 1: PYTHON SYNTAX & AST COMPILATION CHECKS
# ==============================================================================

def test_python_debugger_missing_colon():
    bad_code = "def greet(name)\n    print('Hello ' + name)"
    explanation, meta = python_debugger.analyze_and_explain(bad_code)
    assert meta["error_category"] == "SyntaxError"
    assert meta["line"] == 1
    assert "Missing Colon" in explanation
    assert "def greet(name):" in explanation


def test_python_debugger_mutable_default():
    bad_code = "def record_event(event, log=[]):\n    log.append(event)\n    return log"
    explanation, meta = python_debugger.analyze_and_explain(bad_code)
    assert meta["error_category"] == "MutableDefaultArgument"
    assert "Mutable Default Parameter Antipattern" in explanation
    assert "log=None" in explanation


def test_python_debugger_sort_assignment():
    bad_code = "items = [3, 1, 2]\nitems = items.sort()\nprint(items)"
    explanation, meta = python_debugger.analyze_and_explain(bad_code)
    assert meta["error_category"] == "InPlaceMethodAssignment"
    assert "In-Place Method Assignment" in explanation


def test_python_debugger_runtime_type_error():
    bad_code = "count = 5\nmsg = 'Items left: ' + count\nprint(msg)"
    explanation, meta = python_debugger.analyze_and_explain(bad_code)
    assert meta["error_category"] == "TypeError"
    assert "TypeError: can only concatenate str" in explanation


def test_python_debugger_runtime_zero_division():
    bad_code = "x = 100\ny = 0\nresult = x / y"
    explanation, meta = python_debugger.analyze_and_explain(bad_code)
    assert meta["error_category"] == "ZeroDivisionError"
    assert "ZeroDivisionError" in explanation


def test_python_debugger_clean_execution():
    clean_code = "def square(n):\n    return n * n\n\nval = square(7)\nprint(f'Result: {val}')"
    explanation, meta = python_debugger.analyze_and_explain(clean_code)
    assert meta["status"] == "code_executes_cleanly"
    assert "Result: 49" in explanation
    assert "Code Compiles & Executes Successfully" in explanation


def test_python_debugger_separates_trailing_question_and_flags_average_formula():
    prompt = (
        "num_students = 4\n"
        "total_score = 45\n"
        "average = total_score / num_students - 1\n"
        "print('Average score is:', average)\n\n"
        "it prints 10.25 so it is correct; if not, explain what is wrong?"
    )
    explanation, metadata = python_debugger.analyze_and_explain(prompt)
    assert metadata["error_category"] == "AverageFormulaAdjustment"
    assert metadata["line"] == 3
    assert metadata["input_kind"] == "python_code_with_question"
    assert "it prints 10.25" not in metadata["extracted_code"]
    assert "average = total_score / num_students - 1" in explanation
    assert "average = total_score / num_students" in explanation
    assert "11.25" in explanation


def test_python_debugger_handles_arbitrary_post_division_formula():
    prompt = (
        "total = 20\n"
        "people = 4\n"
        "score = total / people + 2\n"
        "print(score)\n\n"
        "It prints 7.0. Is this correct or wrong?"
    )
    explanation, metadata = python_debugger.analyze_and_explain(prompt)
    assert metadata["error_category"] == "PostDivisionAdjustment"
    assert metadata["line"] == 3
    assert "score = total / people" in explanation
    assert "score = total / people + 2" in explanation


def test_python_debugger_reports_claimed_output_mismatch():
    prompt = (
        "value = 2 * 3\n"
        "print(value)\n\n"
        "It prints 7. Is the output correct?"
    )
    explanation, metadata = python_debugger.analyze_and_explain(prompt)
    assert metadata["error_category"] == "OutputMismatch"
    assert "question says" in explanation
    assert "`6`" in explanation


# ==============================================================================
# TEST 2: GENERAL PROBLEM SOLVER
# ==============================================================================

def test_general_solver_linear_equation():
    query = "solve 3x + 5 = 20"
    explanation, meta = general_solver.solve_and_explain(query)
    assert meta["problem_type"] == "linear_equation"
    assert "3x = 15" in explanation
    assert "x = \\mathbf{5}" in explanation or "x = \\mathbf{5.0}" in explanation or "5" in explanation


def test_general_solver_quadratic_equation():
    query = "solve x^2 - 5x + 6 = 0"
    explanation, meta = general_solver.solve_and_explain(query)
    assert meta["problem_type"] == "quadratic_equation"
    assert "Discriminant" in explanation
    assert "2.00" in explanation
    assert "3.00" in explanation


def test_general_solver_percentage():
    query = "What is 15% of 240?"
    explanation, meta = general_solver.solve_and_explain(query)
    assert meta["problem_type"] == "percentage_calculation"
    assert "36.00" in explanation


def test_general_solver_arithmetic():
    query = "calculate 14 * 25"
    explanation, meta = general_solver.solve_and_explain(query)
    assert meta["problem_type"] == "arithmetic_evaluation"
    assert "350" in explanation


# ==============================================================================
# TEST 3: API ENDPOINT INTEGRATION
# ==============================================================================

def test_api_python_debug_endpoint(client: FlaskClient):
    payload = {
        "code": "def divide_numbers(a, b)\n    return a / b",
        "learner_id": "test_py_student",
    }
    res = client.post("/api/python/debug", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "Missing Colon" in data["explanation"]
    assert data["metadata"]["error_category"] == "SyntaxError"


def test_api_llm_answer_handles_python_code(client: FlaskClient):
    payload = {
        "question": "Why does my code give an error?\n```python\ndef total(prices)\n    return sum(prices)\n```",
        "subject": "Python",
    }
    res = client.post("/api/llm/answer", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert "Missing Colon" in data["answer"]
    assert "def total(prices):" in data["answer"]


def test_api_llm_answer_solves_arbitrary_math(client: FlaskClient):
    payload = {
        "question": "Can you solve 4x - 8 = 16 step by step?",
        "subject": "Mathematics",
    }
    res = client.post("/api/llm/answer", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert "Linear Equation" in data["answer"]
    assert "6" in data["answer"]


def test_api_llm_answer_returns_targeted_math_practice(client: FlaskClient):
    res = client.post("/api/llm/answer", json={
        "question": "Why is 1/4 + 1/6 = 1/5 wrong?",
        "subject": "Mathematics",
        "learner_id": "practice_math_student",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["misconception"] == "M1_add_across"
    assert data["practice_set"]["subject"] == "Mathematics"
    assert data["practice_set"]["count"] == 6
    assert all(item["type"] == "math" for item in data["practice_set"]["questions"])


def test_api_llm_answer_returns_targeted_code_practice(client: FlaskClient):
    res = client.post("/api/llm/answer", json={
        "question": "Why does this Python function fail?\n```python\ndef total(values)\n    return sum(values)\n```",
        "subject": "Python",
        "learner_id": "practice_code_student",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["misconception"] == "SyntaxError"
    assert data["practice_set"]["subject"] == "Python"
    assert data["practice_set"]["count"] == 6
    assert all(item["type"] == "code" for item in data["practice_set"]["questions"])


def test_api_practice_submit_and_progress(client: FlaskClient):
    import time
    learner_id = f"practice_submit_student_{int(time.time() * 1000)}"
    res = client.post("/api/practice/submit", json={
        "learner_id": learner_id,
        "session_id": "practice_session_1",
        "practice_id": "math_M1_add_across_1",
        "subject": "Mathematics",
        "misconception": "M1_add_across",
        "answer": "5/12",
        "correct_answer": "5/12",
    })
    assert res.status_code == 200
    assert res.get_json()["correct"] is True

    progress = client.get(f"/api/practice/progress?learner_id={learner_id}")
    assert progress.status_code == 200
    record = progress.get_json()["records"][0]
    assert record["attempts"] == 1
    assert record["accuracy"] == 1.0


def test_code_practice_contains_solution_and_explanation(client: FlaskClient):
    response = client.post("/api/llm/answer", json={
        "subject": "Python",
        "question": "def greet(name)\n    return name",
    })
    assert response.status_code == 200
    question = response.get_json()["practice_set"]["questions"][0]
    assert question["correct_code"]
    assert question["explanation"]


def test_code_practice_submit_returns_solution(client: FlaskClient):
    response = client.post("/api/practice/submit", json={
        "learner_id": "solution_student",
        "session_id": "solution_session",
        "practice_id": "code_SyntaxError_1",
        "subject": "Python",
        "misconception": "SyntaxError",
        "answer": "def greet(name):\n    return f'Hello {name}'",
        "reference_code": "def greet(name)\n    return f'Hello {name}'",
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["correct_code"]
    assert data["explanation"]
