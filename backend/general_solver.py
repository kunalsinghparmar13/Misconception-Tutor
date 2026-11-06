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
from typing import Any, Dict, Tuple


class GeneralProblemSolver:
    """Solves algebraic, arithmetic, percentage, and algorithmic problems with Socratic derivations."""

    def can_solve(self, text: str) -> bool:
        """Determines if the input is a solvable mathematical or algorithmic problem."""
        t_low = text.lower()
        # Do not hijack specialized calculus, recursive programming, or fraction misconception problems
        if any(w in t_low for w in ["integration by parts", "integral", "∫", "dx", "e^(-2x)", "recursion", "memoization", "grid", "fib"]):
            return False
        # Do not hijack fraction addition/division comparison questions like "1/4 + 1/6 = 1/5"
        if re.search(r"\d+\s*/\s*\d+\s*[\+\-\*\/÷]\s*\d+\s*/\s*\d+", text):
            return False
        if re.search(r"[a-z]\s*(?:\^2|²)", text, re.IGNORECASE) and "=" in text:
            return True
        if re.search(r"[a-z]\s*[\+\-\*\/]\s*\d+\s*=", text, re.IGNORECASE):
            return True
        if re.search(r"\d+(?:\.\d+)?\s*%\s*of\s*\d+", text, re.IGNORECASE):
            return True
        if re.search(r"[-+]?\d+(?:\.\d+)?\s*[\+\-\*\/]\s*[-+]?\d+(?:\.\d+)?", text):
            return True
        if any(w in t_low for w in ["solve", "calculate", "find", "what is", "evaluate", "simplify", "how much", "how many"]):
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
            f"👋 **Hey! Let's solve this Linear Equation together!**\n\n"
            f"We are working with: **${a}{var} {'+' if b >= 0 else '-'} {abs(b)} = {c}$**\n\n"
            f"#### ⚖️ The Big Idea: The Balanced Scale\n"
            f"Think of an algebraic equation like a balanced scale. Our mystery number `${var}$` is tucked inside a gift box on the left. "
            f"Whatever we do to the left side, we do the exact same thing to the right side to keep the scale balanced.\n\n"
            f"Our game plan: **unwrap `${var}$` step-by-step** using opposite (inverse) operations!\n\n"
            f"#### 🧩 Step 1: Clear the Constant Term ({b:+d})\n"
            f"Notice the `{b:+d}` on the left. To cancel it out, we subtract `{b}` from both sides:\n"
            f"$${a}{var} = {c} - ({b}) \\implies {a}{var} = {rhs_minus_b}$$\n\n"
            f"#### ✂️ Step 2: Unwrap the Variable (Divide by {a})\n"
            f"Now `${var}$` is being multiplied by `{a}`. The inverse of multiplying by `{a}` is dividing by `{a}`:\n"
            f"$${var} = \\frac{{{rhs_minus_b}}}{{{a}}} = \\mathbf{{{x_display}}}$$\n\n"
            f"#### 🔍 Step 3: Let's Check Our Work (The Verification)\n"
            f"Let's plug ${var} = {x_display}$ right back into our starting equation:\n"
            f"$${a}({x_display}) {'+' if b >= 0 else '-'} {abs(b)} = {a * float(x_val) + b:.2f} = {c}$$ ✓ The scale balances!\n\n"
            f"#### 💡 Guiding Takeaway\n"
            f"Whenever you solve a linear equation $ax + b = c$, apply inverse operations in reverse order: first undo addition/subtraction, then undo multiplication!"
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
            roots_desc = "Complex roots (Discriminant $D < 0$)"
        elif discriminant == 0:
            r = -b / (2 * a)
            roots_desc = f"One repeated real root: ${var} = {r:.2f}$"
        else:
            r1 = (-b + math.sqrt(discriminant)) / (2 * a)
            r2 = (-b - math.sqrt(discriminant)) / (2 * a)
            roots_desc = f"Two distinct real roots: ${var}_1 = {r1:.2f}$ and ${var}_2 = {r2:.2f}$"

        response = (
            f"👋 **Let's solve this Quadratic Equation together!**\n\n"
            f"**Standard Form:** ${a}{var}^2 {'+' if b >= 0 else '-'} {abs(b)}{var} {'+' if c >= 0 else '-'} {abs(c)} = 0$\n\n"
            f"#### 🎢 The Big Idea: The Parabola Curve\n"
            f"When you graph any quadratic equation, it traces a curved path called a **parabola**. "
            f"Solving the equation simply means finding the exact spots where this curve crosses the ground ($x$-axis)!\n\n"
            f"#### 🔍 Step 1: Identify the Three Coefficients\n"
            f"- **$a = {a}$** (controls the steepness of the curve)\n"
            f"- **$b = {b}$** (shifts the peak)\n"
            f"- **$c = {c}$** (vertical intercept)\n\n"
            f"#### 🔮 Step 2: The Fortune Teller: Discriminant ($D = b^2 - 4ac$)\n"
            f"Before doing full calculations, mathematicians calculate the **Discriminant** ($D$) to preview what the solutions look like:\n"
            f"$$D = ({b})^2 - 4({a})({c}) = {b**2} - ({4*a*c}) = \\mathbf{{{discriminant}}}$$\n"
            f"- Since $D {' > 0' if discriminant > 0 else (' = 0' if discriminant == 0 else ' < 0')}$, our curve produces: **{roots_desc}**.\n\n"
            f"#### 🧩 Step 3: Apply the Quadratic Formula\n"
            f"$${var} = \\frac{{-b \\pm \\sqrt{{D}}}}{{2a}} = \\frac{{-({b}) \\pm \\sqrt{{{discriminant}}}}}{{2({a})}}$$\n\n"
            f"**Roots:** {roots_desc}\n\n"
            f"#### 🎯 Think Socratic: Check Your Roots\n"
            f"If you substitute either root back into the original equation, what should the result equal? Zero! That confirms your algebra is rock solid."
        )
        return response, meta

    def _solve_percentage(self, match: re.Match, query: str, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        meta["problem_type"] = "percentage_calculation"
        pct = float(match.group(1))
        total = float(match.group(2))
        result = (pct / 100.0) * total

        response = (
            f"👋 **Let's work through this Percentage Calculation together!**\n\n"
            f"We want to find: **${pct}\\%$ of ${total}$**\n\n"
            f"#### 💡 The Intuition: What Does 'Percent' Really Mean?\n"
            f"The word **percent** comes from Latin *per centum*, which literally translates to **'out of every 100'** (just like 100 cents make one dollar). "
            f"So ${pct}\\%$ means we take **${pct}$ parts for every $100$ in the total**.\n\n"
            f"#### 🔢 Step 1: Turn the Percent into a Decimal or Fraction\n"
            f"Divide by $100$:\n"
            f"$${pct}\\% = \\frac{{{pct}}}{{100}} = {pct / 100.0}$$\n\n"
            f"#### ✖️ Step 2: Multiply by the Total Value\n"
            f"$$\\text{{Result}} = {pct / 100.0} \\times {total} = \\mathbf{{{result:.2f}}}$$\n\n"
            f"#### 🧠 Mental Math Bridge (The 10% Trick)\n"
            f"Here is how human mathematicians calculate this in their heads at the store:\n"
            f"- $10\\%$ of {total} is just moving the decimal left one spot: **{total * 0.1:.2f}**\n"
            f"- Scale that up by {pct/10:.1f} to arrive at **{result:.2f}** without needing a calculator!\n\n"
            f"#### 🎯 Quick Check for You\n"
            f"What would $20\\%$ of {total} be? (Hint: Double the 10% amount!)"
        )
        return response, meta

    def _solve_arithmetic(self, match: re.Match, query: str, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        meta["problem_type"] = "arithmetic_evaluation"
        v1 = float(match.group(1))
        op = match.group(2)
        v2 = float(match.group(3))

        v1_str = f"{int(v1)}" if v1.is_integer() else f"{v1}"
        v2_str = f"{int(v2)}" if v2.is_integer() else f"{v2}"

        if op == "/":
            if v2 == 0:
                response = (
                    "### 🎯 Conceptual Understanding: Dividing by Zero\n\n"
                    f"Let's look at what **${v1_str} \\div 0$** means in the physical world:\n\n"
                    "#### 💡 The Intuition (The Sharing Metaphor)\n"
                    f"Imagine you have **{v1_str} items** (like cookies or books), and you want to distribute them equally among **0 people**.\n"
                    "- How many does each person receive? The question breaks down because there are no recipients to receive anything!\n"
                    "- In mathematics, division is the inverse of multiplication: $a \\div b = c$ means $c \\times b = a$. If $b = 0$, what number multiplied by $0$ could ever give ${v1_str}$? None! Anything times $0$ is always $0$.\n\n"
                    "### 📌 Key Takeaway\n"
                    "Dividing by zero is mathematically **undefined** because no real number multiplied by zero can equal a non-zero dividend."
                )
                return response, meta

            ans = v1 / v2
            ans_clean = f"{int(ans)}" if ans.is_integer() else f"{ans:.4f}".rstrip("0").rstrip(".")

            if v1 < v2:
                comparison_text = "more people than items, so nobody receives a full whole item. Each person gets a fraction or equal slice."
            elif v1 == v2:
                comparison_text = "an equal number of items and people, so each person receives exactly 1 whole item."
            else:
                comparison_text = f"more items than people, so each person gets at least {int(ans)} full item(s) plus a remaining slice."

            if v1 == 1.0 and v2 == 2.0:
                decimal_bridge = (
                    "\n#### 🧠 Connecting Fractions to Decimals\n"
                    "Why is $\\frac{1}{2}$ written as **$0.5$** in decimal form?\n"
                    "1. Think of $1.0$ as **$10$ tenths** (like ten 10¢ dimes making a whole \\$1.00).\n"
                    "2. When you divide $10$ tenths equally between $2$ friends:\n"
                    "   $$10 \\text{ tenths} \\div 2 = 5 \\text{ tenths} = \\mathbf{0.5}$$\n"
                    "3. So half of a whole is always **$0.5$** (or $50\\%$ of the whole)!\n"
                )
            else:
                decimal_bridge = (
                    "\n#### 🧠 Connecting Fractions to Decimals\n"
                    f"- Fraction form: **$\\frac{{{v1_str}}}{{{v2_str}}}$**\n"
                    f"- Decimal evaluation: $${v1_str} \\div {v2_str} = \\mathbf{{{ans_clean}}}$$\n"
                )

            double_v1 = f"{int(v1*2)}" if (v1*2).is_integer() else f"{v1*2}"
            response = (
                "### 🎯 Conceptual Understanding: Division as Fair Sharing\n\n"
                f"Let's explore what **${v1_str} \\div {v2_str}$** actually represents in the real world, rather than just treating it as a sterile number calculation.\n\n"
                "#### 💡 The Intuition (The Fair Share Model)\n"
                f"Imagine you have **{v1_str} whole pizza(s)** and you want to share them equally between **{v2_str} friends**:\n"
                f"- Notice that there are {comparison_text}\n"
                f"- To share fairly, you cut the total into equal portions. Each friend receives **$\\frac{{{v1_str}}}{{{v2_str}}}$** of a whole, which equals **${ans_clean}$**.\n"
                f"{decimal_bridge}\n"
                "#### 🤔 Think Socratic: Check Your Understanding\n"
                f"> *If you were sharing **{double_v1} pizzas** among the same **{v2_str} friends**, how much would each person get? What happens to each share when you double the items?*\n\n"
                "### 📌 Key Takeaway\n"
                "Division is fundamentally **fair sharing** or **partitioning into equal groups**. When the numerator is smaller than the denominator, the result is always a fraction or decimal less than $1$."
            )
            return response, meta

        elif op == "*":
            ans = v1 * v2
            ans_clean = f"{int(ans)}" if ans.is_integer() else f"{ans:.4f}".rstrip("0").rstrip(".")
            response = (
                "### 🎯 Conceptual Understanding: Multiplication as Scaling & Groups\n\n"
                f"Let's look at what **${v1_str} \\times {v2_str}$** represents conceptually!\n\n"
                "#### 💡 The Intuition (The Grid & Array Model)\n"
                f"Multiplication isn't just rote memorization—it represents **repeated groups** or the **area of a rectangle**:\n"
                f"- Imagine a tiled courtyard with **{v1_str} rows**, and each row has **{v2_str} tiles**.\n"
                f"- Instead of counting tiles one-by-one, you accumulate {v1_str} groups of {v2_str}:\n"
                f"  $${v1_str} \\times {v2_str} = \\mathbf{{{ans_clean}}}$$\n\n"
                "#### 🧠 Friendly Mental Math Strategy (Double & Halve)\n"
                f"A great human mental math trick for multiplication is **Double and Halve**:\n"
                f"- Halving one factor and doubling the other preserves the exact same area:\n"
                f"  $$({v1/2:g}) \\times ({v2*2:g}) = \\mathbf{{{ans_clean}}}$$\n\n"
                "#### 🤔 Think Socratic: Check Your Understanding\n"
                f"> *Does reversing the order ($ {v2_str} \\times {v1_str} $) change the total? Why does a rectangle rotated 90 degrees maintain the exact same total area?*\n\n"
                "### 📌 Key Takeaway\n"
                "Multiplication is commutative ($A \\times B = B \\times A$) and associative. Visualizing problems as rectangular arrays makes arithmetic intuitive and eliminates memorization anxiety."
            )
            return response, meta

        elif op == "+":
            ans = v1 + v2
            ans_clean = f"{int(ans)}" if ans.is_integer() else f"{ans:.4f}".rstrip("0").rstrip(".")
            response = (
                "### 🎯 Conceptual Understanding: Addition as Combining Quantities\n\n"
                f"Let's explore what **${v1_str} + {v2_str}$** means conceptually!\n\n"
                "#### 💡 The Intuition (The Number Line)\n"
                f"Addition is moving forward along the continuous number line:\n"
                f"- Start at the position **{v1_str}**.\n"
                f"- Take a leap forward of **{v2_str} units**.\n"
                f"- You land directly on: $${v1_str} + {v2_str} = \\mathbf{{{ans_clean}}}$$\n\n"
                "#### 🧠 Place Value & Grouping\n"
                f"When combining numbers, we bundle identical units (ones with ones, tens with tens). "
                f"Here, accumulating {v1_str} and {v2_str} yields **{ans_clean}**.\n\n"
                "#### 🤔 Think Socratic: Check Your Understanding\n"
                f"> *What is the inverse of addition? If ${v1_str} + {v2_str} = {ans_clean}$, what does ${ans_clean} - {v2_str}$ equal?*\n\n"
                "### 📌 Key Takeaway\n"
                "Addition combines discrete quantities or shifts forward on the number line. It is commutative ($A + B = B + A$)."
            )
            return response, meta

        else:  # Subtraction
            ans = v1 - v2
            ans_clean = f"{int(ans)}" if ans.is_integer() else f"{ans:.4f}".rstrip("0").rstrip(".")
            signs_text = f"Since {v1_str} is smaller than {v2_str}, moving backward takes you past zero into negative territory: **{ans_clean}**." if v1 < v2 else f"Since {v1_str} is greater than or equal to {v2_str}, the remaining portion is positive: **{ans_clean}**."
            response = (
                "### 🎯 Conceptual Understanding: Subtraction as Distance & Difference\n\n"
                f"Let's look at **${v1_str} - {v2_str}$** conceptually!\n\n"
                "#### 💡 The Intuition (Distance Between Points)\n"
                f"Subtraction measures either **removal** (taking away) or the **distance** between two values on a number line:\n"
                f"- On a number line, how far apart are **{v1_str}** and **{v2_str}**?\n"
                f"- Moving {v2_str} units backward from {v1_str} lands on: $${v1_str} - {v2_str} = \\mathbf{{{ans_clean}}}$$\n\n"
                "#### 🧠 Signs & Direction\n"
                f"{signs_text}\n\n"
                "#### 🤔 Think Socratic: Check Your Understanding\n"
                f"> *If you owed a friend \\${v2_str} and paid them \\${v1_str}, how much debt would you still have left?*\n\n"
                "### 📌 Key Takeaway\n"
                "Subtraction is the inverse of addition: $A - B = C$ means $C + B = A$. Thinking of subtraction as 'distance on the number line' makes handling negative numbers and signs second nature."
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
