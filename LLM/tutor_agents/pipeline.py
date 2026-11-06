"""Orchestrates the four agents and streams progress events."""

from __future__ import annotations

import os
import threading
import time
import uuid
from collections import OrderedDict
from typing import Any, Dict, Iterator, List, Optional

from . import grounding as gr
from .agents import (
    Check,
    ExplainerAgent,
    PracticeAgent,
    PracticeItem,
    ReviewerAgent,
    SolverAgent,
    build_review,
)
from .model_client import ModelClient, ModelUnavailable

AGENT_ORDER = ["explainer", "solver", "practice", "reviewer"]
MIN_PRACTICE = 3


class _BoundedStore:
    """Remembers generated practice items so grading never trusts client-supplied answers."""

    def __init__(self, limit: int = 3000) -> None:
        self._data: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._limit = limit
        self._lock = threading.Lock()

    def put_many(self, items: Dict[str, Dict[str, Any]]) -> None:
        with self._lock:
            for key, value in items.items():
                self._data[key] = value
                self._data.move_to_end(key)
            while len(self._data) > self._limit:
                self._data.popitem(last=False)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._data.get(key)


practice_store = _BoundedStore()


def _ev(event: str, **kw: Any) -> Dict[str, Any]:
    return {"event": event, **kw}


class TutorPipeline:
    def __init__(
        self,
        client: Optional[ModelClient] = None,
        practice_count: Optional[int] = None,
        max_revisions: int = 1,
    ) -> None:
        self.client = client or ModelClient()
        self.practice_count = practice_count or int(os.getenv("PRACTICE_COUNT", "6"))
        self.max_revisions = max_revisions
        self.explainer = ExplainerAgent(self.client)
        self.solver = SolverAgent(self.client)
        self.practice = PracticeAgent(self.client)
        self.reviewer = ReviewerAgent(self.client)

    # ------------------------------------------------------------------ status
    def status(self) -> Dict[str, Any]:
        health = self.client.health()
        return {
            "configured": self.client.configured,
            "reachable": bool(health.get("reachable")),
            "mode": self.client.mode,
            "model": health.get("model") or self.client.model_name,
            "error": health.get("error"),
            "agents": AGENT_ORDER,
        }

    # ------------------------------------------------------------------ running
    def run(self, question: str, subject: str = "Mathematics", **kw: Any) -> Dict[str, Any]:
        final: Optional[Dict[str, Any]] = None
        for event in self.stream(question, subject, **kw):
            if event["event"] == "error":
                raise ModelUnavailable(event["message"])  # already the public message
            if event["event"] == "complete":
                final = event["result"]
        if final is None:  # pragma: no cover - defensive
            raise ModelUnavailable("The pipeline ended without a result.")
        return final

    def stream(
        self,
        question: str,
        subject: str = "Mathematics",
        practice_count: Optional[int] = None,
        review_with_model: bool = True,
    ) -> Iterator[Dict[str, Any]]:
        started = time.time()
        count = max(3, min(8, int(practice_count or self.practice_count)))
        timings: Dict[str, float] = {}
        revisions = 0

        yield _ev("start", agents=AGENT_ORDER)
        grounding = gr.ground(question, subject)
        yield _ev("grounding", data=grounding.to_dict())

        # ---- Agent 1: explanation ------------------------------------------------
        yield _ev("agent_start", agent="explainer")
        try:
            t = time.time()
            explanation = self.explainer.run(question, grounding)
            timings["explainer"] = round(time.time() - t, 2)
        except ModelUnavailable as exc:
            yield _ev("error", agent="explainer", status="model_unavailable", message=exc.public_message)
            return
        yield _ev("agent_result", agent="explainer", data=explanation.to_dict())

        # ---- Agent 2: correct answer / code (with one verified retry) -------------
        yield _ev("agent_start", agent="solver")
        try:
            t = time.time()
            solution = self.solver.run(question, grounding)
            solution_checks = self.reviewer.check_solution(grounding, solution)
            if any(c.status == "fail" for c in solution_checks) and revisions < self.max_revisions:
                revisions += 1
                issues = [c.detail for c in solution_checks if c.status == "fail"]
                yield _ev("revision", agent="solver", issues=issues)
                solution = self.solver.run(question, grounding, feedback=issues)
                solution_checks = self.reviewer.check_solution(grounding, solution)
            timings["solver"] = round(time.time() - t, 2)
        except ModelUnavailable as exc:
            yield _ev("error", agent="solver", status="model_unavailable", message=exc.public_message)
            return
        yield _ev("agent_result", agent="solver", data=solution.to_dict())

        # ---- Agent 3: practice problems -------------------------------------------
        label = explanation.misconception or grounding.misconception_id or ""
        yield _ev("agent_start", agent="practice")
        items: List[PracticeItem] = []
        practice_checks: List[Check] = []
        t = time.time()
        prefix = f"pr_{uuid.uuid4().hex[:8]}"
        try:
            items = self.practice.run(question, grounding, label, count=count, id_prefix=prefix)
            practice_checks = self.reviewer.verify_practice(grounding, items)
            if len(items) < MIN_PRACTICE and revisions < self.max_revisions + 1:
                yield _ev("revision", agent="practice", issues=[f"Only {len(items)} usable practice problems; asking for more."])
                more = self.practice.run(
                    question, grounding, label, count=count,
                    avoid=[i.prompt for i in items], id_prefix=f"{prefix}b",
                )
                self.reviewer.verify_practice(grounding, more)
                items.extend(more)
                items = items[:count]
                practice_checks = [self._practice_summary(items)]
        except ModelUnavailable as exc:
            practice_checks = [Check("practice_items_verified", "warn", f"Practice agent failed: {exc}")]
        timings["practice"] = round(time.time() - t, 2)
        practice_set = self._practice_set(grounding, label, items)
        practice_store.put_many({q["id"]: q for q in practice_set["questions"]})
        yield _ev("agent_result", agent="practice", data=practice_set)

        # ---- Agent 4: review --------------------------------------------------------
        yield _ev("agent_start", agent="reviewer")
        t = time.time()
        checks: List[Check] = list(solution_checks) + self.reviewer.check_explanation(grounding, explanation) + practice_checks
        verdict, notes = None, ""
        if review_with_model:
            try:
                crit = self.reviewer.critique(question, explanation, solution, checks)
                verdict, notes = crit["verdict"], crit["notes"]
                if verdict:
                    checks.append(Check("model_review", "warn" if verdict == "FAIL" else "pass",
                                        notes or ("Reviewer model found no problems." if verdict == "PASS" else "Reviewer model flagged a concern.")))
            except ModelUnavailable as exc:
                checks.append(Check("model_review", "skip", f"Reviewer model unavailable: {exc}"))
        review = build_review(checks, verdict, notes, revisions, round(time.time() - t, 2))
        timings["reviewer"] = review.seconds
        yield _ev("agent_result", agent="reviewer", data=review.to_dict())

        result = {
            "status": "success",
            "question": question,
            "subject": subject,
            "grounding": grounding.to_dict(),
            "explanation": explanation.to_dict(),
            "solution": solution.to_dict(),
            "practice_set": practice_set,
            "review": review.to_dict(),
            "misconception": label or grounding.misconception_id or "general",
            "model": explanation.model,
            "timings": {**timings, "total": round(time.time() - started, 2)},
        }
        result["answer"] = compose_markdown(result)
        yield _ev("complete", result=result)

    # ------------------------------------------------------------------ helpers
    def _practice_summary(self, items: List[PracticeItem]) -> Check:
        verified = sum(1 for i in items if i.verified)
        if not items:
            return Check("practice_items_verified", "warn", "No usable practice problems were produced.")
        return Check("practice_items_verified", "pass" if verified else "warn", f"{verified}/{len(items)} practice problems machine-verified.")

    @staticmethod
    def _practice_set(grounding: gr.Grounding, label: str, items: List[PracticeItem]) -> Dict[str, Any]:
        subject = "Python" if grounding.is_code else "Mathematics"
        target = label or grounding.misconception_id or "general"
        questions = []
        for item in items:
            q = item.to_dict()
            q.update(subject=subject, target_misconception=target, generated_by="fine-tuned model")
            questions.append(q)
        return {"subject": subject, "misconception": target, "count": len(questions), "questions": questions}


def compose_markdown(result: Dict[str, Any]) -> str:
    explanation, solution, review = result["explanation"], result["solution"], result["review"]
    parts = ["## Why this went wrong", explanation["text"], "## The correct " + ("code" if solution["kind"] == "code" else "answer"), solution["text"]]
    run = solution.get("run")
    if solution["kind"] == "code" and run:
        out = (run.get("stdout") or "").strip()
        parts.append("**Output when this code was actually run:**\n```\n" + (out or "(no output)") + "\n```" if run.get("success") else f"**Running this code failed:** {run.get('error_type')}: {run.get('error_message')}")
    status = "all checks passed" if review["approved"] and review["verified"] else "approved, but some parts could not be machine-verified" if review["approved"] else "NOT fully verified - see issues"
    parts.append(f"## Review ({status})")
    parts.extend(f"- [{c['status']}] {c['detail']}" for c in review["checks"])
    return "\n\n".join(parts)


_pipeline: Optional[TutorPipeline] = None
_pipeline_lock = threading.Lock()


def get_pipeline() -> TutorPipeline:
    global _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            _pipeline = TutorPipeline()
        return _pipeline


def set_pipeline(pipeline: Optional[TutorPipeline]) -> None:
    """Replace the shared pipeline (used by tests)."""
    global _pipeline
    with _pipeline_lock:
        _pipeline = pipeline
