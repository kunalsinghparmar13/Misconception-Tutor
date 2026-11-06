"""The four agents. Each one is a prompt + parser around the user's fine-tuned model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from . import grounding as gr
from . import parsing, prompts
from .model_client import ChatResult, ModelClient

EXPLAIN_HEADINGS = {
    "misconception": ["misconception"],
    "what_went_wrong": ["what went wrong", "where it went wrong", "the mistake"],
    "why_mistake": ["why you made this mistake", "why this mistake happens", "why you made that mistake", "why it happens"],
    "correct_thinking": ["how to think about it correctly", "the right way to think", "correct thinking", "how to fix it"],
    "check_yourself": ["check yourself", "try this"],
}


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " ..."


@dataclass
class Explanation:
    text: str
    sections: Dict[str, str]
    misconception: str
    model: str
    seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Solution:
    kind: str  # "math" | "code"
    text: str
    final_answer: Optional[str]
    steps: str
    code: Optional[str]
    what_changed: str
    run: Optional[Dict[str, Any]]
    model: str
    seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PracticeItem:
    id: str
    type: str  # "math" | "code"
    prompt: str
    correct_answer: Optional[str] = None
    code: Optional[str] = None
    correct_code: Optional[str] = None
    expected_output: Optional[str] = None
    explanation: str = ""
    verified: bool = False
    verification: str = "unchecked"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Agent:
    name = "agent"
    max_tokens = 512
    temperature = 0.2

    def __init__(self, client: ModelClient) -> None:
        self.client = client

    def _ask(self, system: str, user: str) -> ChatResult:
        return self.client.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )


# ------------------------------------------------------------------------------ agent 1
class ExplainerAgent(Agent):
    """Why is the learner's answer wrong, and why did they make that mistake?"""

    name = "explainer"
    max_tokens = 520

    def run(self, question: str, grounding: gr.Grounding, feedback: Optional[List[str]] = None) -> Explanation:
        user = f"Learner's message:\n{question}\n"
        if grounding.facts_block():
            user += f"\n{grounding.facts_block()}\n"
        if feedback:
            user += "\nA reviewer found problems with your previous attempt. Fix them:\n" + "\n".join(f"- {f}" for f in feedback) + "\n"
        res = self._ask(prompts.EXPLAINER, user)
        sections = parsing.split_sections(res.text, EXPLAIN_HEADINGS)
        label = (sections.get("misconception") or parsing.find_field(res.text, ["misconception"]) or "").split("\n")[0].strip(" .*")
        label = _clip(label, 80) or (grounding.misconception_id or "")
        return Explanation(text=res.text, sections=sections, misconception=label, model=res.model, seconds=res.seconds)


# ------------------------------------------------------------------------------ agent 2
class SolverAgent(Agent):
    """Correct answer for maths, correct code for programming."""

    name = "solver"
    max_tokens = 600
    temperature = 0.1

    def run(self, question: str, grounding: gr.Grounding, feedback: Optional[List[str]] = None) -> Solution:
        is_code = grounding.is_code
        system = prompts.SOLVER_CODE if is_code else prompts.SOLVER_MATH
        # The adapter was fine-tuned to answer learners Socratically, so a learner's chatty message
        # ("my answer was ...") makes it ask a question back. Give the solver a direct task instead,
        # repeat the format in the user turn (small models weight it more than the system turn).
        if is_code:
            user = (
                "Task: write the corrected, complete Python program for the learner's problem below. "
                "Do not ask questions. Start your reply with 'Corrected code:'.\n\n"
                f"Learner's problem:\n{question}\n"
            )
        else:
            problem = grounding.expression or question
            user = (
                "Task: solve this maths problem yourself and show the steps. Do not ask the learner anything. "
                "Start your reply with 'Final answer:', then 'Steps:' as a numbered list, then 'Check:'.\n\n"
                f"Problem: {problem}\n"
            )
            if grounding.expression and grounding.expression != question:
                user += f"(The learner wrote: {question})\n"
        if grounding.facts_block():
            user += f"\n{grounding.facts_block()}\n"
        if feedback:
            user += "\nA reviewer found problems with your previous attempt. Fix them:\n" + "\n".join(f"- {f}" for f in feedback) + "\n"
        res = self._ask(system, user)
        if is_code:
            code = parsing.first_python_block(res.text)
            changed = parsing.find_field(res.text, ["what changed"]) or ""
            run = gr.run_code(code) if code else None
            return Solution("code", res.text, None, "", code, changed, run, res.model, res.seconds)
        final = parsing.find_field(res.text, ["final answer", "answer"])
        sections = parsing.split_sections(res.text, {"steps": ["steps", "solution steps"], "check": ["check"]})
        return Solution("math", res.text, final, sections.get("steps", ""), None, "", None, res.model, res.seconds)


# ------------------------------------------------------------------------------ agent 3
class PracticeAgent(Agent):
    """Fresh practice problems for the same misconception."""

    name = "practice"
    max_tokens = 1000
    temperature = 0.5

    def run(
        self,
        question: str,
        grounding: gr.Grounding,
        misconception: str,
        count: int = 6,
        avoid: Optional[List[str]] = None,
        id_prefix: str = "pr",
    ) -> List[PracticeItem]:
        # Ask in small batches: one long generation can exceed the ~100 s per-request limit of free
        # tunnels (Cloudflare 524) on a T4, and short batches also parse more reliably.
        items: List[PracticeItem] = []
        seen = list(avoid or [])
        attempts = 0
        while len(items) < count and attempts < count + 1:
            attempts += 1
            # code exercises are ~4x longer than maths ones, so ask for one at a time
            size = 1 if grounding.is_code else self.batch_size
            want = min(size, count - len(items))
            batch = self._run_batch(question, grounding, misconception, want, seen, f"{id_prefix}{attempts}")
            for item in batch:
                if item.prompt not in seen:
                    seen.append(item.prompt)
                    items.append(item)
        for i, item in enumerate(items, start=1):
            item.id = f"{id_prefix}_{i}"
        return items[:count]

    batch_size = 3

    def _run_batch(
        self,
        question: str,
        grounding: gr.Grounding,
        misconception: str,
        count: int,
        avoid: List[str],
        id_prefix: str,
    ) -> List[PracticeItem]:
        label = misconception or grounding.misconception_id or "the mistake in the learner's work"
        system = (prompts.PRACTICE_CODE if grounding.is_code else prompts.PRACTICE_MATH).format(count=count, misconception=label)
        user = f"The learner's original problem:\n{_clip(question, 1200)}\n"
        if grounding.facts_block():
            user += f"\n{grounding.facts_block()}\n"
        if avoid:
            user += "\nDo not repeat these problems:\n" + "\n".join(f"- {_clip(a, 120)}" for a in avoid) + "\n"
        res = self.client.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=min(self.max_tokens, 200 * count + 120),
            temperature=self.temperature,
        )
        items: List[PracticeItem] = []
        for i, raw in enumerate(parsing.parse_practice(res.text), start=1):
            if grounding.is_code:
                code, fixed = raw.get("code"), raw.get("correct_code")
                if not (code and fixed):
                    continue
                items.append(PracticeItem(
                    id=f"{id_prefix}_{i}", type="code", prompt=raw.get("question", "Fix this code."),
                    code=code, correct_code=fixed, explanation=raw.get("why", ""),
                ))
            else:
                if not (raw.get("question") and raw.get("answer")):
                    continue
                items.append(PracticeItem(
                    id=f"{id_prefix}_{i}", type="math", prompt=raw["question"],
                    correct_answer=raw["answer"].strip(), explanation=raw.get("why", ""),
                ))
        return items  # keep extras; run() caps the total


# ------------------------------------------------------------------------------ agent 4
@dataclass
class Check:
    name: str
    status: str  # pass | fail | warn | skip
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Review:
    approved: bool
    verified: bool
    checks: List[Check]
    issues: List[str]
    model_verdict: Optional[str] = None
    model_notes: str = ""
    revisions: int = 0
    seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["checks"] = [c.to_dict() for c in self.checks]
        return d


class ReviewerAgent(Agent):
    """Checks everything. Exact tools decide pass/fail; the model adds an advisory critique."""

    name = "reviewer"
    max_tokens = 220
    temperature = 0.0

    # ---- deterministic checks -------------------------------------------------
    def check_solution(self, grounding: gr.Grounding, solution: Solution) -> List[Check]:
        checks: List[Check] = []
        if solution.kind == "math":
            if grounding.verified_answer is None:
                checks.append(Check("answer_matches_exact_value", "skip", "This kind of problem cannot be computed exactly by the tools, so the answer is not machine-verified."))
            elif not solution.final_answer:
                checks.append(Check("answer_matches_exact_value", "fail", "The solver did not give a clearly marked 'Final answer'."))
            else:
                expected = gr.parse_number(grounding.verified_answer)
                got = gr.parse_number(solution.final_answer)
                if expected is not None and got is not None and expected == got:
                    checks.append(Check("answer_matches_exact_value", "pass", f"Final answer {solution.final_answer} equals the exact value {grounding.verified_answer}."))
                else:
                    checks.append(Check("answer_matches_exact_value", "fail", f"Solver answered '{solution.final_answer}' but the exact value is {grounding.verified_answer}."))
        else:
            if not solution.code:
                checks.append(Check("code_runs", "fail", "The solver did not provide a Python code block."))
            elif solution.run is None:
                checks.append(Check("code_runs", "skip", "No sandbox available to run the code."))
            elif solution.run.get("success"):
                out = (solution.run.get("stdout") or "").strip()
                checks.append(Check("code_runs", "pass", "Corrected code was executed in the sandbox without errors" + (f"; it printed {out[:120]!r}." if out else ".")))
            else:
                checks.append(Check("code_runs", "fail", f"Corrected code raised {solution.run.get('error_type')} at line {solution.run.get('line')}: {solution.run.get('error_message')}"))
        return checks

    def check_explanation(self, grounding: gr.Grounding, explanation: Explanation) -> List[Check]:
        checks: List[Check] = []
        required = ["what_went_wrong", "why_mistake", "correct_thinking"]
        missing = [k for k in required if k not in explanation.sections]
        if missing:
            checks.append(Check("explanation_structure", "warn", "Explanation is missing sections: " + ", ".join(m.replace("_", " ") for m in missing) + "."))
        else:
            checks.append(Check("explanation_structure", "pass", "Explanation covers what went wrong, why the mistake happens and the correct idea."))
        if grounding.verified_answer and grounding.kind != "python":
            expected = gr.parse_number(grounding.verified_answer)
            if expected is not None and expected not in gr.numbers_in(explanation.text):
                checks.append(Check("explanation_mentions_exact_value", "warn", f"Explanation never states the exact value {grounding.verified_answer}."))
        if grounding.is_code and grounding.code_run and not grounding.code_run.get("success"):
            etype = str(grounding.code_run.get("error_type") or "")
            if etype and etype.lower() not in explanation.text.lower():
                checks.append(Check("explanation_mentions_error", "warn", f"Explanation never mentions the real error ({etype})."))
        return checks

    def verify_practice(self, grounding: gr.Grounding, items: List[PracticeItem]) -> List[Check]:
        """Mutates ``items``: sets verified/verification and *drops* items proven wrong."""
        kept: List[PracticeItem] = []
        dropped: List[str] = []
        for item in items:
            if item.type == "math":
                status = self._verify_math_item(item)
            else:
                status = self._verify_code_item(item)
            if status == "wrong":
                dropped.append(item.prompt[:60])
                continue
            kept.append(item)
        items[:] = kept
        checks: List[Check] = []
        verified = sum(1 for i in items if i.verified)
        if not items:
            checks.append(Check("practice_items_verified", "warn", "No usable practice problems were produced."))
        else:
            detail = f"{verified}/{len(items)} practice problems machine-verified"
            if dropped:
                detail += f"; {len(dropped)} dropped because their stated answer was wrong or the reference code failed"
            checks.append(Check("practice_items_verified", "pass" if verified else "warn", detail + "."))
        return checks

    @staticmethod
    def _verify_math_item(item: PracticeItem) -> str:
        probe = gr.ground(item.prompt, "Mathematics")
        if probe.verified_answer is None or probe.kind == "python":
            item.verification = "not machine-checkable"
            return "unknown"
        stated, exact = gr.parse_number(item.correct_answer or ""), gr.parse_number(probe.verified_answer)
        if stated is None or exact is None or stated != exact:
            return "wrong"
        item.verified, item.verification = True, "answer computed exactly"
        return "ok"

    @staticmethod
    def _verify_code_item(item: PracticeItem) -> str:
        ref = gr.run_code(item.correct_code or "")
        if ref is None:
            item.verification = "no sandbox"
            return "unknown"
        if not ref.get("success"):
            return "wrong"
        item.expected_output = (ref.get("stdout") or "").strip()
        buggy = gr.run_code(item.code or "") or {}
        buggy_differs = (not buggy.get("success")) or (buggy.get("stdout", "").strip() != item.expected_output)
        if not buggy_differs:
            return "wrong"  # the "buggy" code behaves exactly like the fix: not a real exercise
        item.verified, item.verification = True, "reference code executed; buggy code behaves differently"
        return "ok"

    # ---- model critique (advisory) --------------------------------------------
    def critique(self, question: str, explanation: Explanation, solution: Solution, checks: List[Check]) -> Dict[str, str]:
        summary = "\n".join(f"- {c.name}: {c.status} - {c.detail}" for c in checks)
        user = (
            f"Learner's message:\n{_clip(question, 800)}\n\n"
            f"EXPLANATION:\n{_clip(explanation.text, 1100)}\n\n"
            f"SOLUTION:\n{_clip(solution.text, 900)}\n\n"
            f"AUTOMATIC CHECKS:\n{summary}\n"
        )
        res = self._ask(prompts.REVIEWER, user)
        verdict = (parsing.find_field(res.text, ["verdict"]) or "").upper()
        verdict = "FAIL" if verdict.startswith("FAIL") else "PASS" if verdict.startswith("PASS") else ""
        issues = parsing.find_field(res.text, ["issues"]) or ""
        suggestion = parsing.find_field(res.text, ["suggestion"]) or ""
        notes = "; ".join(p for p in (issues if issues.lower() != "none" else "", suggestion if suggestion.lower() != "none" else "") if p)
        return {"verdict": verdict, "notes": notes}


def build_review(checks: List[Check], model_verdict: Optional[str], model_notes: str, revisions: int, seconds: float) -> Review:
    failed = [c for c in checks if c.status == "fail"]
    passed = [c for c in checks if c.status == "pass"]
    issues = [c.detail for c in failed]
    return Review(
        approved=not failed,
        verified=bool(passed) and not failed,
        checks=checks,
        issues=issues,
        model_verdict=model_verdict or None,
        model_notes=model_notes,
        revisions=revisions,
        seconds=seconds,
    )
