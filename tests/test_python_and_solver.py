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
