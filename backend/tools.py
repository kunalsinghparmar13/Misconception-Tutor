"""
================================================================================
ECC Agentic Tool Suite: Mathematical Verification & Diagnostic Tools
Provides mathematical tool definitions and execution functions for LLM providers.
================================================================================
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from llm.core.types import ToolDefinition
from llm.tools.executor import ToolExecutor, ToolRegistry
from backend import backend_code

tool_registry = ToolRegistry()


# ------------------------------------------------------------------------------
# Tool 1: Fraction Operation Calculator
# ------------------------------------------------------------------------------
CHECK_FRACTION_DEF = ToolDefinition(
    name="calculate_fraction_op",
    description="Calculates exact arithmetic sum or quotient of two fractions a/b and c/d.",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "integer", "description": "Numerator of first fraction"},
            "b": {"type": "integer", "description": "Denominator of first fraction"},
            "c": {"type": "integer", "description": "Numerator of second fraction"},
            "d": {"type": "integer", "description": "Denominator of second fraction"},
            "operation": {"type": "string", "enum": ["add", "divide"], "description": "Operation to perform"},
        },
        "required": ["a", "b", "c", "d", "operation"],
    },
)


def calculate_fraction_op(a: int, b: int, c: int, d: int, operation: str) -> str:
    f1 = Fraction(a, b)
    f2 = Fraction(c, d)
    if operation == "add":
        result = f1 + f2
        op_sym = "+"
    elif operation == "divide":
        result = f1 / f2
        op_sym = "÷"
    else:
        return f"Unknown operation: {operation}"
    return f"{a}/{b} {op_sym} {c}/{d} = {result.numerator}/{result.denominator} (approx {float(result):.4f})"


tool_registry.register(CHECK_FRACTION_DEF, calculate_fraction_op)


# ------------------------------------------------------------------------------
# Tool 2: Brown & Burton Buggy Rule Diagnoser
# ------------------------------------------------------------------------------
DIAGNOSE_BUG_DEF = ToolDefinition(
    name="diagnose_buggy_fraction",
    description="Tests student answer against Brown & Burton (1978) M1-M5 buggy rules to find the exact mental misconception.",
    parameters={
        "type": "object",
        "properties": {
            "student_answer": {"type": "string", "description": "The student's submitted answer (e.g. '2/10')"},
            "a": {"type": "integer", "description": "Numerator of first fraction"},
            "b": {"type": "integer", "description": "Denominator of first fraction"},
            "c": {"type": "integer", "description": "Numerator of second fraction"},
            "d": {"type": "integer", "description": "Denominator of second fraction"},
            "operation": {"type": "string", "enum": ["fraction_add", "fraction_div"], "description": "Operation category"},
        },
        "required": ["student_answer", "a", "b", "c", "d"],
    },
)


def diagnose_buggy_fraction(student_answer: str, a: int, b: int, c: int, d: int, operation: str = "fraction_add") -> str:
    student_frac = backend_code.parse_fraction(student_answer)
    if student_frac is None:
        return f"Could not parse '{student_answer}' into a mathematical fraction."

    bug_rules = backend_code.BUGS_ADD if operation == "fraction_add" else backend_code.BUGS_DIV
    for bug_id, bug_fn in bug_rules.items():
        try:
            top, bot = bug_fn(a, b, c, d)
            if bot != 0 and Fraction(top, bot) == student_frac:
                explanation = backend_code.EXPLANATIONS.get(bug_id, {})
                title = explanation.get("title", bug_id)
                hint = explanation.get("fix_hint", "")
                return f"MATCHED BUG [{bug_id}]: {title}. Remediation hint: {hint}"
        except Exception:
            continue

    return "No canonical buggy rule matched. Answer may be an arithmetic calculation slip."


tool_registry.register(DIAGNOSE_BUG_DEF, diagnose_buggy_fraction)


# ------------------------------------------------------------------------------
# Tool 3: Python Code Compiler & Safe Execution
# ------------------------------------------------------------------------------
RUN_PYTHON_DEF = ToolDefinition(
    name="compile_and_run_python",
    description="Compiles and executes Python code in a safe sandbox, capturing output or syntax/runtime errors.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source code to compile and run"},
        },
        "required": ["code"],
    },
)


def compile_and_run_python(code: str) -> str:
    from backend.python_debugger import python_debugger
    explanation, metadata = python_debugger.analyze_and_explain(code)
    return explanation


tool_registry.register(RUN_PYTHON_DEF, compile_and_run_python)


# Global tool executor
math_tool_executor = ToolExecutor(tool_registry)
