"""Orchestrates the four agents and streams progress events."""

from __future__ import annotations

import copy
import os
import threading
import time
import uuid
from collections import OrderedDict
from typing import Any, Dict, Iterator, List, Optional

from . import grounding as gr
from .agents import (
    fast_mode,
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
practice_sessions = _BoundedStore(limit=1000)  # one entry per practice round (set_id)

MASTERY_THRESHOLD = 0.8  # >= 80% of a round correct means the misconception is mastered: stop practising


def _next_level(current: str, accuracy: float) -> str:
    """Below 50%: one step easier. 50-79%: same difficulty, new problems. (>= 80% stops, see round_status)."""
    ladder = ["easier", "same", "harder"]
    base = "same" if current == "start" else current
    idx = ladder.index(base) if base in ladder else 1
    if accuracy < 0.5:
        idx = max(0, idx - 1)
    return ladder[idx]


def round_status(session: Dict[str, Any]) -> Dict[str, Any]:
    total = len(session["ids"])
    results = session["results"]
    answered = sum(1 for i in session["ids"] if i in results)
    correct = sum(1 for i in session["ids"] if results.get(i))
    complete = total > 0 and answered >= total
    accuracy = (correct / total) if total else 0.0
    mastered = complete and accuracy >= MASTERY_THRESHOLD
    return {
        "set_id": session["set_id"], "round": session["round"], "level": session["level"],
        "total": total, "answered": answered, "correct": correct,
        "accuracy": round(accuracy, 3), "threshold": MASTERY_THRESHOLD,
        "complete": complete, "mastered": mastered,
        "next_level": None if (mastered or not complete) else _next_level(session["level"], accuracy),
    }


def record_practice_result(set_id: str, practice_id: str, correct: bool, answer: str) -> Optional[Dict[str, Any]]:
    """Record the learner's FIRST attempt at an item of a round; returns the round status."""
    session = practice_sessions.get(set_id)
    if not session or practice_id not in session["ids"]:
        return None
    with practice_sessions._lock:
        if practice_id not in session["results"]:
            session["results"][practice_id] = bool(correct)
            session["answers"][practice_id] = (answer or "")[:400]
    return round_status(session)


def _ev(event: str, **kw: Any) -> Dict[str, Any]:
    return {"event": event, **kw}


class TutorPipeline:
    def __init__(
        self,
        client: Optional[ModelClient] = None,
        practice_count: Optional[int] = None,
        max_revisions: Optional[int] = None,
    ) -> None:
        self.client = client or ModelClient()
        self.fast = fast_mode()
        self.practice_count = practice_count or int(os.getenv("PRACTICE_COUNT", "3" if self.fast else "6"))
        # Each retry is another full model call; fast mode skips them and relies on the checks to flag problems.
        self.max_revisions = max_revisions if max_revisions is not None else (0 if self.fast else 1)
        self._cache_on = os.getenv("TUTOR_CACHE", "1").strip().lower() not in {"0", "false", "no", "off"}
        self._cache: OrderedDict = OrderedDict()
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
        review_with_model: Optional[bool] = None,
    ) -> Iterator[Dict[str, Any]]:
        started = time.time()
        if review_with_model is None:
            review_with_model = not self.fast  # the model critique is advisory; the exact checks always run
        count = max(3, min(8, int(practice_count or self.practice_count)))
        timings: Dict[str, float] = {}
        revisions = 0

        yield _ev("start", agents=AGENT_ORDER)
        cache_key = (question.strip().lower(), subject.strip().lower(), count, bool(review_with_model))
        cached = self._cache.get(cache_key) if self._cache_on else None
        if cached is not None:  # identical question answered recently: replay instantly, no model calls
            yield _ev("grounding", data=cached["grounding"])
            # Fresh practice round (new ids, empty score) so a replay never inherits an earlier learner's answers.
            replay_set = copy.deepcopy(cached["practice_set"])
            new_id = f"pr_{uuid.uuid4().hex[:8]}"
            for i, q in enumerate(replay_set.get("questions", []), start=1):
                q["id"] = f"{new_id}_{i}"
            self._open_round(replay_set, new_id, question, subject, replay_set.get("misconception", ""),
                             round_no=1, level="start", history=[])
            replayed = {**cached, "practice_set": replay_set}
            for agent, key in (("explainer", "explanation"), ("solver", "solution"), ("practice", "practice_set"), ("reviewer", "review")):
                yield _ev("agent_start", agent=agent)
                yield _ev("agent_result", agent=agent, data=replayed[key])
            yield _ev("complete", result={**replayed, "cached": True, "timings": {"total": 0.0}})
            return
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
            items = self._round_items(question, grounding, label, count, prefix)
            practice_checks = [self._practice_summary(items)]
        except ModelUnavailable as exc:
            practice_checks = [Check("practice_items_verified", "warn", f"Practice agent failed: {exc}")]
        timings["practice"] = round(time.time() - t, 2)
        practice_set = self._practice_set(grounding, label, items)
        self._open_round(practice_set, prefix, question, subject, label, round_no=1, level="start", history=[])
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
        if self._cache_on and review.approved:
            self._cache[cache_key] = result
            while len(self._cache) > 200:
                self._cache.popitem(last=False)
        yield _ev("complete", result=result)

    # ------------------------------------------------------------------ helpers
    def _practice_summary(self, items: List[PracticeItem]) -> Check:
        verified = sum(1 for i in items if i.verified)
        if not items:
            return Check("practice_items_verified", "warn", "No usable practice problems were produced.")
        return Check("practice_items_verified", "pass" if verified else "warn", f"{verified}/{len(items)} practice problems machine-verified.")

    @staticmethod
    def _open_round(practice_set: Dict[str, Any], set_id: str, question: str, subject: str, label: str,
                    round_no: int, level: str, history: List[str]) -> None:
        ids = [q["id"] for q in practice_set["questions"]]
        for q in practice_set["questions"]:
            q["set_id"] = set_id
        practice_set.update(set_id=set_id, round=round_no, level=level, mastery_threshold=MASTERY_THRESHOLD)
        practice_store.put_many({q["id"]: q for q in practice_set["questions"]})
        practice_sessions.put_many({set_id: {
            "set_id": set_id, "question": question, "subject": subject, "misconception": label,
            "round": round_no, "level": level, "ids": ids, "results": {}, "answers": {},
            "history": history + [q["prompt"] for q in practice_set["questions"]],
        }})

    def _round_items(self, question: str, grounding: gr.Grounding, label: str, count: int, prefix: str,
                     level: str = "start", mistakes: Optional[List[str]] = None,
                     avoid: Optional[List[str]] = None) -> List[PracticeItem]:
        """Generate, verify (drops wrong ones) and top up once, so a round has enough problems to judge 80%."""
        avoid = list(avoid or [])
        items = self.practice.run(question, grounding, label, count=count, avoid=avoid, id_prefix=prefix,
                                  level=level, mistakes=mistakes)
        self.reviewer.verify_practice(grounding, items)
        if len(items) < count:
            more = self.practice.run(question, grounding, label, count=count - len(items),
                                     avoid=avoid + [i.prompt for i in items], id_prefix=f"{prefix}b",
                                     level=level, mistakes=mistakes)
            self.reviewer.verify_practice(grounding, more)
            items.extend(more)
        items = items[:count]
        for i, item in enumerate(items, start=1):
            item.id = f"{prefix}_{i}"
        return items

    def next_practice(self, set_id: str) -> Dict[str, Any]:
        """New round of different problems after a round scored below the mastery threshold."""
        session = practice_sessions.get(set_id)
        if not session:
            raise KeyError("Unknown practice round.")
        status = round_status(session)
        if not status["complete"]:
            raise ValueError("Answer every problem in this round first.")
        if status["mastered"]:
            raise ValueError("This round is already mastered; no more practice is needed.")
        level = status["next_level"]
        grounding = gr.ground(session["question"], session["subject"])
        mistakes = []
        for pid in session["ids"]:
            if not session["results"].get(pid):
                item = practice_store.get(pid) or {}
                mistakes.append(f"{item.get('prompt', '')} -> learner answered: {session['answers'].get(pid, '')[:120]}")
        count = len(session["ids"]) or self.practice_count
        new_id = f"pr_{uuid.uuid4().hex[:8]}"
        items = self._round_items(session["question"], grounding, session["misconception"], count, new_id,
                                  level=level, mistakes=mistakes, avoid=session["history"])
        practice_set = self._practice_set(grounding, session["misconception"], items)
        self._open_round(practice_set, new_id, session["question"], session["subject"], session["misconception"],
                         round_no=session["round"] + 1, level=level, history=session["history"])
        practice_set["previous"] = status
        return practice_set

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
