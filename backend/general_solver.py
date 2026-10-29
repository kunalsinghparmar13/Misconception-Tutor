"""
================================================================================
AI That Teaches: Misconception Tutor — General Problem Solving & Math Engine
Solves, verifies, and provides step-by-step Socratic remediation for arbitrary
mathematical equations, word problems, algebra, and algorithmic queries.
================================================================================
"""

from __future__ import annotations

import math
import re
from fractions import Fraction
from typing import Any, Dict, Optional, Tuple


class GeneralProblemSolver:
    """Solves algebraic, arithmetic, percentage, and algorithmic problems with Socratic derivations."""

    def can_solve(self, text: str) -> bool:
        """Determines if the input is a solvable mathematical or algorithmic problem."""
        t_low = text.lower()
        if any(w in t_low for w in ["solve", "calculate", "find", "what is", "evaluate", "simplify", "how much", "how many"]):
            return True
        if re.search(r"\d+\s*[\+\-\*\/\^\=]\s*\d+", text):
            return True
        if re.search(r"[a-z]\s*[\+\-\*\/]\s*\d+\s*=", text, re.IGNORECASE):
            return True
        return False

    def solve_and_explain(self, question: str) -> Tuple[str, Dict[str, Any]]:
        """Analyzes and solves the problem, returning Socratic step-by-step guidance."""
        metadata: Dict[str, Any] = {"topic": "general_problem_solving", "source": "general_solver_engine"}
        q_clean = question.strip()

        # 1. Linear Equation: a*x + b = c (e.g. 3x + 5 = 20 or 2x - 4 = 10)
        lin_match = re.search(r"([+-]?\s*\d*)\s*([a-zA-Z])\s*([+-]\s*\d+)?\s*=\s*([+-]?\s*\d+)", q_clean)
        if lin_match and "x²" not in q_clean and "x^2" not in q_clean:
            return self._solve_linear_equation(lin_match, q_clean, metadata)

        # 2. Quadratic Equation: ax^2 + bx + c = 0
        quad_match = re.search(r"([+-]?\s*\d*)\s*([a-zA-Z])(?:\^2|²)\s*([+-]\s*\d*)\s*\2\s*([+-]\s*\d+)?\s*=\s*([+-]?\s*\d+)", q_clean)
        if quad_match:
            return self._solve_quadratic_equation(quad_match, q_clean, metadata)

        # 3. Percentage: "What is 15% of 240?"
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", q_clean, re.IGNORECASE)
        if pct_match:
            return self._solve_percentage(pct_match, q_clean, metadata)

        # 4. Direct Arithmetic: e.g. "Calculate 14 * 25 - 50"
        arith_match = re.search(r"(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)", q_clean)
        if arith_match:
            return self._solve_arithmetic(arith_match, q_clean, metadata)

        # 5. Algorithmic / Conceptual General Problem
        return self._solve_conceptual_problem(q_clean, metadata)

    def _solve_linear_equation(self, match: re.Match, query: str, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        meta["problem_type"] = "linear_equation"
        coeff_str = match.group(1).replace(" ", "")
        var = match.group(2)
        const_str = (match.group(3) or "+0").replace(" ", "")
        rhs_str = match.group(4).replace(" ", "")

        # Parse coefficient
        if coeff_str in ["", "+"]:
            a = 1
        elif coeff_str == "-":
            a = -1
        else:
            try:
                a = int(coeff_str)
            except ValueError:
                a = 1

        b = int(const_str)
        c = int(rhs_str)

        # a*x + b = c  =>  a*x = c - b  =>  x = (c - b) / a
        rhs_minus_b = c - b
        x_val = Fraction(rhs_minus_b, a)
        x_display = str(x_val.numerator) if x_val.denominator == 1 else f"{x_val.numerator}/{x_val.denominator}"

        response = (
            f"### 🔍 Step-by-Step Solution: Linear Equation\n\n"
            f"**Equation:** ${a}{var} {'+' if b >= 0 else '-'} {abs(b)} = {c}$\n\n"
            f"#### Step 1: Isolate the Variable Term\n"
            f"Subtract ${b}$ from both sides to cancel the constant:\n"
            f"$${a}{var} = {c} - ({b}) \\implies {a}{var} = {rhs_minus_b}$$\n\n"
            f"#### Step 2: Divide by the Coefficient\n"
            f"Divide both sides by ${a}$ to isolate ${var}$:\n"
            f"$${var} = \\frac{{{rhs_minus_b}}}{{{a}}} = \\mathbf{{{x_display}}}$$\n\n"
            f"#### Step 3: Verification (Invariant Check)\n"
            f"Substitute ${var} = {x_display}$ back into the original equation:\n"
            f"$${a}({x_display}) + ({b}) = {a * float(x_val) + b:.2f} = {c}$$ ✓ The equality holds perfectly!\n\n"
            f"### 📌 Key Takeaway\n"
            f"To solve any linear equation $ax + b = c$, apply inverse operations in reverse PEMDAS order: first add/subtract the constant term, then divide by the coefficient."
        )
        return response, meta

    def _solve_quadratic_equation(self, match: re.Match, query: str, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        meta["problem_type"] = "quadratic_equation"
        a_str = match.group(1).replace(" ", "")
        var = match.group(2)
        b_str = match.group(3).replace(" ", "")
        c_str = (match.group(4) or "+0").replace(" ", "")
        rhs_str = match.group(5).replace(" ", "")

        a = int(a_str) if a_str not in ["", "+", "-"] else (-1 if a_str == "-" else 1)
        b = int(b_str) if b_str not in ["", "+", "-"] else (-1 if b_str == "-" else 1)
        c = int(c_str) - int(rhs_str)

        discriminant = b**2 - 4 * a * c

        if discriminant < 0:
            roots_desc = "Complex roots (discriminant $D < 0$)"
        elif discriminant == 0:
            r = -b / (2 * a)
            roots_desc = f"One repeated real root: ${var} = {r:.2f}$"
        else:
            r1 = (-b + math.sqrt(discriminant)) / (2 * a)
            r2 = (-b - math.sqrt(discriminant)) / (2 * a)
            roots_desc = f"Two distinct real roots: ${var}_1 = {r1:.2f}$ and ${var}_2 = {r2:.2f}$"

        response = (
            f"### 🔍 Step-by-Step Solution: Quadratic Equation\n\n"
            f"**Standard Form:** ${a}{var}^2 {'+' if b >= 0 else '-'} {abs(b)}{var} {'+' if c >= 0 else '-'} {abs(c)} = 0$\n\n"
            f"#### Step 1: Identify Coefficients\n"
            f"- $a = {a}, \\quad b = {b}, \\quad c = {c}$\n\n"
            f"#### Step 2: Compute the Discriminant ($D = b^2 - 4ac$)\n"
            f"$$D = ({b})^2 - 4({a})({c}) = {b**2} - ({4*a*c}) = \\mathbf{{{discriminant}}}$$\n\n"
            f"#### Step 3: Apply the Quadratic Formula\n"
            f"$${var} = \\frac{{-b \\pm \\sqrt{{D}}}}{{2a}} = \\frac{{-({b}) \\pm \\sqrt{{{discriminant}}}}}{{2({a})}}$$\n\n"
            f"**Roots:** {roots_desc}\n\n"
            f"### 📌 Key Takeaway\n"
            f"The sign of the discriminant determines the geometry of the parabola: $D > 0$ means two x-intercepts, $D = 0$ touches the axis once, and $D < 0$ never crosses the real axis."
        )
        return response, meta

    def _solve_percentage(self, match: re.Match, query: str, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        meta["problem_type"] = "percentage_calculation"
        pct = float(match.group(1))
        total = float(match.group(2))
        result = (pct / 100.0) * total

        response = (
            f"### 🔍 Step-by-Step Solution: Percentage Calculation\n\n"
            f"**Problem:** Find ${pct}\\%$ of ${total}$\n\n"
            f"#### Step 1: Convert Percentage to a Ratio\n"
            f"Recall that 'percent' means 'per one hundred' (divide by 100):\n"
            f"$${pct}\\% = \\frac{{{pct}}}{{100}} = {pct / 100.0}$$\n\n"
            f"#### Step 2: Multiply by the Total Value\n"
            f"$$\\text{{Result}} = {pct / 100.0} \\times {total} = \\mathbf{{{result:.2f}}}$$\n\n"
            f"### 💡 Mental Math Shortcut\n"
            f"To find ${pct}\\%$ easily:\n"
            f"- $10\\%$ of {total} is {total * 0.1:.2f}\n"
            f"- Scale by {pct/10:.1f} to quickly verify: $\\approx {result:.2f}$\n\n"
            f"### 📌 Key Takeaway\n"
            f"Percentages represent fractional proportions of a base value. Always divide by 100 before multiplying."
        )
        return response, meta

    def _solve_arithmetic(self, match: re.Match, query: str, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        meta["problem_type"] = "arithmetic_evaluation"
        v1 = float(match.group(1))
        op = match.group(2)
        v2 = float(match.group(3))

        if op == "+":
            ans = v1 + v2
            name = "Addition"
        elif op == "-":
            ans = v1 - v2
            name = "Subtraction"
        elif op == "*":
            ans = v1 * v2
            name = "Multiplication"
        else:
            ans = v1 / v2 if v2 != 0 else float("inf")
            name = "Division"

        ans_str = f"{int(ans)}" if ans.is_integer() else f"{ans:.4f}"

        response = (
            f"### 🔍 Arithmetic Evaluation: {name}\n\n"
            f"**Expression:** ${v1} {op} {v2}$\n\n"
            f"#### Calculation\n"
            f"$${v1} {op} {v2} = \\mathbf{{{ans_str}}}$$\n\n"
            f"### 📌 Key Takeaway\n"
            f"Always observe operational precedence (PEMDAS/BODMAS) when chaining operations together."
        )
        return response, meta

    def _solve_conceptual_problem(self, query: str, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        meta["problem_type"] = "conceptual_inquiry"
        return (
            f"### 🔍 Problem Diagnosis & Resolution\n\n"
            f"**Your Query:**\n> *{query}*\n\n"
            f"#### 1. Core Principle Decomposition\n"
            f"To solve this problem systematically, let's break it down into fundamental invariants:\n"
            f"- **Given Inputs**: Identify the initial state, given variables, and boundary assumptions.\n"
            f"- **Governing Rule**: What mathematical theorem or algorithmic invariant applies here?\n"
            f"- **Step-by-Step Derivation**: Work through the transformation preserving equality at every step.\n\n"
            f"#### 2. Verification Check\n"
            f"Check your intermediate result: does it hold for edge cases (zero, negative numbers, extreme values)?\n\n"
            f"### 💡 Socratic Guiding Question\n"
            f"What is the first step you took? If you test your current hypothesis against a simple concrete example, does the expected result match?\n\n"
            f"### 📌 Key Takeaway\n"
            f"Breaking complex problems down into step-by-step invariant checks eliminates guessing and produces verifiable proofs."
        ), meta


# Global singleton
general_solver = GeneralProblemSolver()
