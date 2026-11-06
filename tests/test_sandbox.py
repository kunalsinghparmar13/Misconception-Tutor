"""Tests for the process-isolated Python executor used by the debugger."""

from __future__ import annotations

import os

import pytest

from backend.python_debugger import python_debugger
from backend.sandbox import MAX_OUTPUT_BYTES, run_student_code


def test_clean_code_runs_and_captures_stdout():
    res = run_student_code("def square(n):\n    return n * n\nprint(f'Result: {square(7)}')")
    assert res["success"] is True
    assert "Result: 49" in res["stdout"]


def test_runtime_error_reports_type_message_and_line():
    res = run_student_code("count = 5\nmsg = 'Items left: ' + count\nprint(msg)")
    assert res["success"] is False
    assert res["error_type"] == "TypeError"
    assert "can only concatenate str" in res["error_message"]
    assert res["line"] == 2


def test_infinite_loop_is_stopped():
    res = run_student_code("while True:\n    pass")
    assert res["success"] is False
    assert res["error_type"] == "TimeoutError"


def test_file_access_and_dangerous_imports_are_blocked():
    assert run_student_code("open('/etc/passwd')")["error_type"] == "NameError"
    for module in ("os", "subprocess", "socket", "sys"):
        res = run_student_code(f"import {module}")
        assert res["error_type"] == "ImportError", module


def test_safe_stdlib_imports_and_classes_work():
    res = run_student_code("import math\nclass A:\n    pass\nprint(math.sqrt(16))")
    assert res["success"] is True
    assert "4.0" in res["stdout"]


def test_output_is_truncated():
    res = run_student_code("print('x' * 5000)")
    assert res["success"] is True
    assert len(res["stdout"]) <= MAX_OUTPUT_BYTES


@pytest.mark.skipif(os.name == "nt", reason="POSIX resource limits only")
def test_runaway_output_is_rejected():
    res = run_student_code("print('x' * 10**7)")
    assert res["success"] is False
    assert res["error_type"] == "OutputLimitExceeded"


@pytest.mark.skipif(os.name == "nt", reason="POSIX resource limits only")
def test_memory_bomb_is_rejected():
    res = run_student_code("data = [0] * 10**9")
    assert res["success"] is False
    assert res["error_type"] in {"MemoryError", "ResourceLimitExceeded"}


def test_debugger_uses_sandbox_for_infinite_loops():
    _, meta = python_debugger.analyze_and_explain("while True:\n    pass")
    assert meta["error_category"] == "TimeoutError"
