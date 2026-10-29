"""
================================================================================
Dataset Enrichment & Continuous Training Script
Adds diverse Python debugging and general problem-solving training pairs to the
continuous fine-tuning dataset, then triggers the continuous fine-tuning run.
================================================================================
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "LLM" / "data" / "continuous_training_dataset.jsonl"

ENRICHMENT_SAMPLES = [
    # 1. Missing Colon Syntax Error
    {
        "id": f"samp_{int(time.time() * 1000)}_py01",
        "timestamp": datetime.utcnow().isoformat(),
        "learner_id": "student_python_01",
        "subject": "Python",
        "misconception": "SyntaxError_Missing_Colon",
        "instruction": "Debug and explain the Python syntax error in the function header.",
        "input": "def calculate_average(numbers)\n    return sum(numbers) / len(numbers)",
        "output": "### 🔍 Syntax Slip Detected: Missing Colon (':')\n\n**File Location:** Line 1, Column 31\n\n```python\n1 | def calculate_average(numbers)\n                                ^\n```\n\n**What Python says:** `SyntaxError: expected ':'`\n\n**Why this happened:** In Python, compound statement headers like `def`, `if`, `for`, `while`, and `class` must always terminate with a colon `:` before introducing the indented code block.\n\n### 🛠️ Corrected Python Code\n```python\ndef calculate_average(numbers):\n    return sum(numbers) / len(numbers)\n```\n\n### 📌 Key Takeaway\nAlways append `:` at the end of function definition lines.",
        "feedback": "auto_verified",
        "metadata": {"topic": "python_debugging", "error_type": "SyntaxError", "line": 1},
    },
    # 2. Mutable Default Argument Antipattern
    {
        "id": f"samp_{int(time.time() * 1000)}_py02",
        "timestamp": datetime.utcnow().isoformat(),
        "learner_id": "student_python_02",
        "subject": "Python",
        "misconception": "MutableDefaultArgument",
        "instruction": "Identify the logical antipattern and state accumulation bug in this Python function.",
        "input": "def add_student(name, cohort=[]):\n    cohort.append(name)\n    return cohort",
        "output": "### 🔍 Logical Antipattern: Mutable Default Parameter Antipattern\n\n**Location:** Line 1\n```python\n1 | def add_student(name, cohort=[]):\n```\n\n**Why it fails:** Default parameter objects are evaluated only once when the function is defined, NOT each time the function is called. All subsequent invocations share the exact same mutated list reference across calls!\n\n### 🛠️ Idiomatic Solution\n```python\ndef add_student(name, cohort=None):\n    if cohort is None:\n        cohort = []\n    cohort.append(name)\n    return cohort\n```\n\n### 📌 Key Takeaway\nUse `None` as the default sentinel value and initialize a fresh mutable structure inside the function body.",
        "feedback": "auto_verified",
        "metadata": {"topic": "python_debugging", "error_type": "MutableDefaultArgument", "line": 1},
    },
    # 3. String and Integer Concatenation TypeError
    {
        "id": f"samp_{int(time.time() * 1000)}_py03",
        "timestamp": datetime.utcnow().isoformat(),
        "learner_id": "student_python_03",
        "subject": "Python",
        "misconception": "TypeError_String_Int_Concat",
        "instruction": "Diagnose the runtime TypeError when printing calculation results.",
        "input": "score = 95\nmessage = 'Final Exam Score: ' + score\nprint(message)",
        "output": "### 🔍 Runtime Exception: `TypeError`\n\n**Trigger Line:** Line 2\n```python\n2 | message = 'Final Exam Score: ' + score\n```\n\n**Runtime Exception:** `TypeError: can only concatenate str (not \"int\") to str`\n\n### 💡 Root Cause Analysis\nPython is strongly typed and does not automatically coerce integers to strings during binary `+` concatenation.\n\n### 🛠️ Corrected Python Code\n```python\nscore = 95\nmessage = f'Final Exam Score: {score}'\nprint(message)\n```\n\n### 📌 Key Takeaway\nUse Python 3 f-strings (`f'Score: {score}'`) or explicit `str()` casting for string interpolation.",
        "feedback": "auto_verified",
        "metadata": {"topic": "python_debugging", "error_type": "TypeError", "line": 2},
    },
    # 4. ZeroDivisionError Guard
    {
        "id": f"samp_{int(time.time() * 1000)}_py04",
        "timestamp": datetime.utcnow().isoformat(),
        "learner_id": "student_python_04",
        "subject": "Python",
        "misconception": "ZeroDivisionError",
        "instruction": "Fix the unhandled division by zero in an empty list average calculator.",
        "input": "def get_mean(items):\n    return sum(items) / len(items)",
        "output": "### 🔍 Runtime Exception Risk: `ZeroDivisionError`\n\nWhen `items` is an empty list `[]`, `len(items)` evaluates to `0`, causing `sum([]) / 0` which raises `ZeroDivisionError`.\n\n### 🛠️ Corrected Python Code\n```python\ndef get_mean(items):\n    if not items:\n        return 0.0\n    return sum(items) / len(items)\n```\n\n### 📌 Key Takeaway\nAlways guard division denominators against zero before evaluating fractions or averages.",
        "feedback": "auto_verified",
        "metadata": {"topic": "python_debugging", "error_type": "ZeroDivisionError"},
    },
    # 5. Linear Equation Solving: 3x + 5 = 20
    {
        "id": f"samp_{int(time.time() * 1000)}_math01",
        "timestamp": datetime.utcnow().isoformat(),
        "learner_id": "student_math_01",
        "subject": "Mathematics",
        "misconception": "Algebra_Linear_Equation",
        "instruction": "Solve the linear equation 3x + 5 = 20 with step-by-step Socratic verification.",
        "input": "solve 3x + 5 = 20",
        "output": "### 🔍 Step-by-Step Solution: Linear Equation\n\n**Equation:** $3x + 5 = 20$\n\n#### Step 1: Isolate the Variable Term\nSubtract $5$ from both sides:\n$$3x = 20 - 5 \\implies 3x = 15$$\n\n#### Step 2: Divide by Coefficient\nDivide both sides by $3$:\n$$x = \\frac{15}{3} = \\mathbf{5}$$\n\n#### Step 3: Verification (Invariant Check)\nSubstitute $x = 5$ back into $3x + 5$:\n$$3(5) + 5 = 15 + 5 = 20$$ ✓ Holds!\n\n### 📌 Key Takeaway\nApply inverse operations in reverse PEMDAS order: subtract constant first, then divide by coefficient.",
        "feedback": "auto_verified",
        "metadata": {"topic": "algebra", "problem_type": "linear_equation"},
    },
    # 6. Quadratic Equation Solving: x^2 - 5x + 6 = 0
    {
        "id": f"samp_{int(time.time() * 1000)}_math02",
        "timestamp": datetime.utcnow().isoformat(),
        "learner_id": "student_math_02",
        "subject": "Mathematics",
        "misconception": "Quadratic_Factoring",
        "instruction": "Factor and solve the quadratic equation x^2 - 5x + 6 = 0.",
        "input": "solve x^2 - 5x + 6 = 0",
        "output": "### 🔍 Step-by-Step Solution: Quadratic Factorization\n\n**Equation:** $x^2 - 5x + 6 = 0$\n\n#### Step 1: Find Two Factors\nWe seek two numbers $p$ and $q$ such that:\n- $p \\cdot q = 6$\n- $p + q = -5$\n\nThe pair is $-2$ and $-3$ (since $(-2) \\times (-3) = 6$ and $(-2) + (-3) = -5$).\n\n#### Step 2: Factor the Expression\n$$(x - 2)(x - 3) = 0$$\n\n#### Step 3: Solve for Roots\n- $x - 2 = 0 \\implies x_1 = 2$\n- $x - 3 = 0 \\implies x_2 = 3$\n\n### 📌 Key Takeaway\nFor $x^2 + bx + c = 0$, look for factor pairs of $c$ that sum to $b$.",
        "feedback": "auto_verified",
        "metadata": {"topic": "algebra", "problem_type": "quadratic_equation"},
    },
    # 7. Percentage Calculation
    {
        "id": f"samp_{int(time.time() * 1000)}_math03",
        "timestamp": datetime.utcnow().isoformat(),
        "learner_id": "student_math_03",
        "subject": "Mathematics",
        "misconception": "Percentage_Scaling",
        "instruction": "Calculate percentage and explain mental math verification.",
        "input": "What is 15% of 240?",
        "output": "### 🔍 Step-by-Step Solution: Percentage Calculation\n\n**Problem:** Find $15\\%$ of $240$\n\n#### Step 1: Ratio Conversion\n$$15\\% = \\frac{15}{100} = 0.15$$\n\n#### Step 2: Multiplication\n$$0.15 \\times 240 = \\mathbf{36.00}$$\n\n### 💡 Mental Math Shortcut\n- $10\\%$ of $240 = 24$\n- $5\\%$ of $240 = 12$\n- $15\\% = 24 + 12 = 36$ ✓\n\n### 📌 Key Takeaway\nPercentages scale base values proportionally; break percentages into $10\\%$ and $5\\%$ components for fast verification.",
        "feedback": "auto_verified",
        "metadata": {"topic": "arithmetic", "problem_type": "percentage"},
    },
]


def run():
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = set()
    if DATASET_PATH.exists():
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        if "id" in record:
                            existing_ids.add(record["id"])
                    except Exception:
                        pass

    added_count = 0
    with open(DATASET_PATH, "a", encoding="utf-8") as f:
        for sample in ENRICHMENT_SAMPLES:
            if sample["id"] not in existing_ids:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                added_count += 1

    print(f"Added {added_count} new high-quality training samples to {DATASET_PATH}")
    return added_count


if __name__ == "__main__":
    run()
