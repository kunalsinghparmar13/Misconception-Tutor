"""Deterministic grounding and verification tools.

The model writes every explanation, answer and exercise. These tools only
(a) compute exact facts *before* generation so the prompts are grounded, and
(b) re-check the model's output *after* generation. They never write learner-facing text.
"""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional

PYTHON_SUBJECTS = {"python", "coding", "programming", "computer science", "cs"}

# ----------------------------------------------------------------------------- safe math

class UnsafeExpression(ValueError):
    pass


_BIN = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}


def _num(value: Any) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UnsafeExpression("only plain numbers are allowed")
    return Fraction(str(value)) if isinstance(value, float) else Fraction(value)


def normalize_expression(text: str, implicit_variable: Optional[str] = None) -> str:
    s = text.strip()
    s = s.replace("×", "*").replace("÷", "/").replace("−", "-").replace("–", "-").replace("^", "**")
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)
    s = re.sub(r"(?<=\d)\s*[xX]\s*(?=\d)", "*", s) if implicit_variable is None else s
    if implicit_variable:
        v = re.escape(implicit_variable)
        s = re.sub(rf"(?<=[\d\)])\s*({v})\b", r"*\1", s)
        s = re.sub(rf"\b({v})\s*(?=\()", r"\1*", s)
    s = re.sub(r"(?<=\d)\s*(?=\()", "*", s)
    s = re.sub(r"(?<=\))\s*(?=[\d(])", "*", s)
    return s


def evaluate(expr: str, variables: Optional[Dict[str, Fraction]] = None) -> Fraction:
    """Exact rational evaluation of a small arithmetic expression (no names except variables)."""
    variables = variables or {}
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpression(f"not an arithmetic expression: {exc.msg}") from exc

    def ev(node: ast.AST) -> Fraction:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant):
            return _num(node.value)
        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            raise UnsafeExpression(f"unknown name {node.id!r}")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            v = ev(node.operand)
            return v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Pow):
                base, exp = ev(node.left), ev(node.right)
                if exp.denominator != 1 or abs(exp) > 12 or abs(base) > 10**6:
                    raise UnsafeExpression("exponent too large")
                return base ** int(exp)
            op = _BIN.get(type(node.op))
            if op is None:
                raise UnsafeExpression("operator not allowed")
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Div) and right == 0:
                raise UnsafeExpression("division by zero")
            result = op(left, right)
            if abs(result.numerator).bit_length() > 4000:
                raise UnsafeExpression("number too large")
            return result
        raise UnsafeExpression("expression not allowed")

    return ev(tree)


def fmt(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


_NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:\s*/\s*-?\d+)?")


def parse_number(text: str) -> Optional[Fraction]:
    """Parse '5/12', '0.5', '-3', 'x = 4' ... into a Fraction (first number found)."""
    m = _NUMBER.search((text or "").replace(",", ""))
    if not m:
        return None
    token = m.group(0).replace(" ", "")
    try:
        if "/" in token:
            n, d = token.split("/")
            return Fraction(int(float(n)), int(float(d))) if float(d) != 0 else None
        return Fraction(token)
    except (ValueError, ZeroDivisionError):
        return None


def numbers_in(text: str) -> List[Fraction]:
    out = []
    for m in _NUMBER.finditer((text or "").replace(",", "")):
        n = parse_number(m.group(0))
        if n is not None:
            out.append(n)
    return out


# ------------------------------------------------------------------------- code running

def run_code(code: str) -> Optional[Dict[str, Any]]:
    """Execute code in the app's process-isolated sandbox. ``None`` if no sandbox is available."""
    try:
        from backend.sandbox import run_student_code
    except Exception:  # noqa: BLE001
        return None
    try:
        result = run_student_code(code)
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error_type": type(exc).__name__, "error_message": str(exc), "line": 1, "stdout": ""}
    return {k: v for k, v in result.items() if k != "globals"}


def looks_like_python(text: str) -> bool:
    if "```" in text:
        return True
    code_like = re.compile(
        r"^\s*(def |class |import |from \S+ import |for .+ in .+:|while .+:|if .+:|elif .+:|else:|try:|except|return |print\(|\w+\s*=\s*\S)"
    )
    return sum(1 for line in text.splitlines() if code_like.match(line)) >= 2 or bool(
        re.search(r"\b(def |import |print\()", text)
    )


def extract_python(text: str) -> Optional[str]:
    from .parsing import first_python_block

    block = first_python_block(text)
    if block:
        return block
    if not looks_like_python(text):
        return None
    try:
        from backend.python_debugger import python_debugger

        code, _, _ = python_debugger.split_input(text)
        return code or None
    except Exception:  # noqa: BLE001
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return "\n".join(lines) or None


# -------------------------------------------------------------------------- grounding

@dataclass
class Grounding:
    kind: str = "general"  # fraction | arithmetic | equation | python | general
    expression: Optional[str] = None
    verified_answer: Optional[str] = None
    student_answer: Optional[str] = None
    student_correct: Optional[bool] = None
    misconception_id: Optional[str] = None
    replay: Optional[str] = None
    code: Optional[str] = None
    code_run: Optional[Dict[str, Any]] = None
    facts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_code(self) -> bool:
        return self.kind == "python"

    def facts_block(self) -> str:
        if not self.facts:
            return ""
        return "Verified facts (computed exactly by tools - trust these over your own mental arithmetic):\n" + "\n".join(
            f"- {f}" for f in self.facts
        )


_FRACTION_OP = re.compile(r"(-?\d+)\s*/\s*(\d+)\s*([+\-*×x÷/])\s*(-?\d+)\s*/\s*(\d+)")
_AFTER_EQ = re.compile(
    r"(?:=|\bgot\b|\bget\b|\banswer(?:\s+is)?\b|\bresult(?:\s+is)?\b|\bgives?\b|\bwrote\b|\bsay\b|\bsaid\b)\s*:?\s*(-?\d+(?:\.\d+)?(?:\s*/\s*\d+)?)",
    re.IGNORECASE,
)
_ARITH_CLAIM = re.compile(
    r"(?P<expr>(?:\(?\s*-?\d[\d.,]*\s*\)?\s*[+\-*/×÷^x]\s*)+\(?\s*-?\d[\d.,]*\s*\)?(?:\s*[+\-*/×÷^x]\s*\(?\s*-?\d[\d.,]*\s*\)?)*)\s*=\s*(?P<ans>-?\d[\d.,]*(?:\s*/\s*\d+)?)"
)
_ARITH_ASK = re.compile(
    r"(?:what\s+is|calculate|compute|evaluate|simplify|find)\s+(?P<expr>[\d\s.,+\-*/×÷^()xX]*\d[\d\s.,+\-*/×÷^()xX]*)\??",
    re.IGNORECASE,
)
_EQUATION = re.compile(r"(?P<lhs>[\dx\s.+\-*/()^]*x[\dx\s.+\-*/()^]*|[\d\s.+\-*/()^]+)\s*=\s*(?P<rhs>[\dx\s.+\-*/()^]+)", re.IGNORECASE)


def _solve_linear(lhs: str, rhs: str) -> Optional[Fraction]:
    try:
        lhs_e = normalize_expression(lhs.lower(), "x")
        r = normalize_expression(rhs.lower(), "x")
        f = lambda x: evaluate(lhs_e, {"x": x}) - evaluate(r, {"x": x})  # noqa: E731
        f0, f1, f2 = f(Fraction(0)), f(Fraction(1)), f(Fraction(2))
    except (UnsafeExpression, ZeroDivisionError):
        return None
    slope = f1 - f0
    if slope == 0 or (f2 - f1) != slope:  # constant or not linear
        return None
    return -f0 / slope


def ground(question: str, subject: str = "") -> Grounding:
    """Compute exact facts about the learner's question. Never raises."""
    try:
        return _ground(question, subject)
    except Exception:  # noqa: BLE001 - grounding must never break the pipeline
        return Grounding()


def _ground(question: str, subject: str) -> Grounding:
    g = Grounding()
    is_python_subject = subject.strip().lower() in PYTHON_SUBJECTS

    # --- fractions (+ buggy-rule detection using the repo's Brown & Burton rules)
    m = _FRACTION_OP.search(question)
    if m and not (is_python_subject and "```" in question):
        a, b, c, d = int(m.group(1)), int(m.group(2)), int(m.group(4)), int(m.group(5))
        op = m.group(3)
        if b != 0 and d != 0:
            fa, fb = Fraction(a, b), Fraction(c, d)
            sym = {"+": "+", "-": "-", "*": "×", "×": "×", "x": "×", "÷": "÷", "/": "÷"}[op]
            try:
                exact = {"+": fa + fb, "-": fa - fb, "×": fa * fb, "÷": fa / fb}[sym]
            except ZeroDivisionError:
                exact = None
            if exact is not None:
                g.kind = "fraction"
                g.expression = f"{a}/{b} {sym} {c}/{d}"
                g.verified_answer = fmt(exact)
                g.facts.append(f"Exact value: {g.expression} = {g.verified_answer}.")
                student = None
                after = question[m.end():]
                sm = _AFTER_EQ.search(after)
                if sm:
                    student = parse_number(sm.group(1))
                if student is not None:
                    g.student_answer = fmt(student)
                    g.student_correct = student == exact
                    g.facts.append(
                        f"The learner's answer {g.student_answer} is {'correct' if g.student_correct else 'NOT correct'}."
                    )
                    if not g.student_correct and sym in {"+", "÷"}:
                        _match_buggy_rule(g, sym, a, b, c, d, student)
                return g

    # --- python code
    if is_python_subject or looks_like_python(question):
        code = extract_python(question)
        if code and (is_python_subject or looks_like_python(code)):
            g.kind = "python"
            g.code = code
            g.code_run = run_code(code)
            run = g.code_run
            if run is None:
                g.facts.append("(The code could not be executed here; reason about it carefully.)")
            elif run.get("success"):
                out = (run.get("stdout") or "").strip()
                g.facts.append(
                    "Running the learner's code succeeded without an exception."
                    + (f" Exact output: {out!r}." if out else " It printed nothing.")
                )
            else:
                g.facts.append(
                    f"Running the learner's code raised {run.get('error_type')} at line {run.get('line')}: "
                    f"{run.get('error_message')}. Output before the error: {(run.get('stdout') or '').strip()!r}."
                )
            return g

    # --- arithmetic claim "12 * 7 = 82"
    m = _ARITH_CLAIM.search(question)
    if m:
        try:
            exact = evaluate(normalize_expression(m.group("expr")))
            claimed = parse_number(m.group("ans"))
        except UnsafeExpression:
            exact, claimed = None, None
        if exact is not None:
            g.kind = "arithmetic"
            g.expression = " ".join(m.group("expr").split())
            g.verified_answer = fmt(exact)
            g.facts.append(f"Exact value: {g.expression} = {g.verified_answer}.")
            if claimed is not None:
                g.student_answer = fmt(claimed)
                g.student_correct = claimed == exact
                g.facts.append(
                    f"The learner's answer {g.student_answer} is {'correct' if g.student_correct else 'NOT correct'}."
                )
            return g

    # --- linear equation in x
    for em in _EQUATION.finditer(question):
        lhs, rhs = em.group("lhs").strip(" ."), em.group("rhs").strip(" .")
        if "x" not in (lhs + rhs).lower():
            continue
        if re.fullmatch(r"\s*x\s*", lhs, re.IGNORECASE) and re.fullmatch(r"\s*-?[\d./]+\s*", rhs):
            continue  # that is an answer ("x = 4"), not the equation
        root = _solve_linear(lhs, rhs)
        if root is None:
            continue
        g.kind = "equation"
        g.expression = f"{' '.join(lhs.split())} = {' '.join(rhs.split())}"
        g.verified_answer = f"x = {fmt(root)}"
        g.facts.append(f"Exact solution of {g.expression}: {g.verified_answer}.")
        rest = question.replace(em.group(0), " ")
        am = re.search(r"\bx\s*=\s*(-?\d+(?:\.\d+)?(?:\s*/\s*\d+)?)", rest, re.IGNORECASE)
        if am:
            claimed = parse_number(am.group(1))
            if claimed is not None:
                g.student_answer = f"x = {fmt(claimed)}"
                g.student_correct = claimed == root
                g.facts.append(
                    f"The learner's answer {g.student_answer} is {'correct' if g.student_correct else 'NOT correct'}."
                )
        return g

    # --- plain "what is 12*7+3?"
    m = _ARITH_ASK.search(question)
    if m:
        expr = m.group("expr").strip(" ?.")
        if re.search(r"\d\s*[+\-*/×÷^xX]\s*\(?\d", expr):
            try:
                exact = evaluate(normalize_expression(expr))
            except UnsafeExpression:
                exact = None
            if exact is not None:
                g.kind = "arithmetic"
                g.expression = " ".join(expr.split())
                g.verified_answer = fmt(exact)
                g.facts.append(f"Exact value: {g.expression} = {g.verified_answer}.")
                return g
    return g


def _match_buggy_rule(g: Grounding, sym: str, a: int, b: int, c: int, d: int, student: Fraction) -> None:
    try:
        from backend import backend_code
    except Exception:  # noqa: BLE001
        return
    rules = backend_code.BUGS_ADD if sym == "+" else backend_code.BUGS_DIV
    for bug_id, fn in rules.items():
        try:
            top, bot = fn(a, b, c, d)
            if bot != 0 and Fraction(top, bot) == student:
                g.misconception_id = bug_id
                try:
                    g.replay = backend_code.generate_replay(bug_id, a, b, c, d)
                except Exception:  # noqa: BLE001
                    g.replay = None
                expl = getattr(backend_code, "EXPLANATIONS", {}).get(bug_id, {})
                title = expl.get("title", bug_id)
                g.facts.append(
                    f"The learner's wrong answer is exactly what the buggy rule '{title}' ({bug_id}) produces"
                    + (f": {g.replay}" if g.replay else ".")
                )
                return
        except Exception:  # noqa: BLE001 - a malformed rule must not break grounding
            continue
