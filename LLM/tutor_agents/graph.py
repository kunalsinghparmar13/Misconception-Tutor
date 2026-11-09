"""The four tutor agents as a LangGraph graph.

    START -> ground -> explainer -> solver --(checks fail, revisions left)--> revise --+
                           |           |                                               |
                         error       error   <-----------------------------------------+
                           v           v
                          END         END     solver/revise --(checks pass or no revisions left)--> solved
                                              solved -> practice -> reviewer -> finish -> END

Every node streams the same progress events the web page already understands
(``grounding``, ``agent_start``, ``revision``, ``agent_result``, ``error``, ``complete``) through
LangGraph's custom stream, so ``TutorPipeline.stream`` only has to forward them.
The agents themselves (prompts, parsing, exact checks) are unchanged; see agents.py.
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from . import grounding as gr
from .agents import Check, build_review
from .model_client import ModelUnavailable

if TYPE_CHECKING:  # pragma: no cover
    from .pipeline import TutorPipeline


class TutorState(TypedDict, total=False):
    # inputs
    question: str
    subject: str
    count: int
    review_with_model: bool
    started: float
    cache_key: Any
    # filled in by the nodes
    grounding: Any
    explanation: Any
    solution: Any
    solution_checks: List[Check]
    solver_started: float
    revisions: int
    label: str
    practice_set: Dict[str, Any]
    practice_checks: List[Check]
    review: Any
    timings: Dict[str, float]
    result: Dict[str, Any]
    stopped: bool


def _emit(event: str, **kw: Any) -> None:
    get_stream_writer()({"event": event, **kw})


def _failed(checks: List[Check]) -> List[str]:
    return [c.detail for c in checks if c.status == "fail"]


def build_tutor_graph(p: "TutorPipeline"):
    """Compile the agent graph for one pipeline (its agents, settings and practice store)."""

    # ---- nodes ------------------------------------------------------------------------
    def ground(state: TutorState) -> Dict[str, Any]:
        g = gr.ground(state["question"], state["subject"])
        _emit("grounding", data=g.to_dict())
        return {"grounding": g, "timings": {}, "revisions": 0, "stopped": False}

    def explainer(state: TutorState) -> Dict[str, Any]:
        _emit("agent_start", agent="explainer")
        t = time.time()
        try:
            explanation = p.explainer.run(state["question"], state["grounding"])
        except ModelUnavailable as exc:
            _emit("error", agent="explainer", status="model_unavailable", message=exc.public_message)
            return {"stopped": True}
        _emit("agent_result", agent="explainer", data=explanation.to_dict())
        return {"explanation": explanation, "timings": {**state["timings"], "explainer": round(time.time() - t, 2)}}

    def solver(state: TutorState) -> Dict[str, Any]:
        _emit("agent_start", agent="solver")
        t = time.time()
        try:
            solution = p.solver.run(state["question"], state["grounding"])
        except ModelUnavailable as exc:
            _emit("error", agent="solver", status="model_unavailable", message=exc.public_message)
            return {"stopped": True}
        return {"solution": solution, "solution_checks": p.reviewer.check_solution(state["grounding"], solution),
                "solver_started": t}

    def revise(state: TutorState) -> Dict[str, Any]:
        issues = _failed(state["solution_checks"])
        _emit("revision", agent="solver", issues=issues)
        try:
            solution = p.solver.run(state["question"], state["grounding"], feedback=issues)
        except ModelUnavailable as exc:
            _emit("error", agent="solver", status="model_unavailable", message=exc.public_message)
            return {"stopped": True}
        return {"solution": solution, "solution_checks": p.reviewer.check_solution(state["grounding"], solution),
                "revisions": state["revisions"] + 1}

    def solved(state: TutorState) -> Dict[str, Any]:
        _emit("agent_result", agent="solver", data=state["solution"].to_dict())
        return {"timings": {**state["timings"], "solver": round(time.time() - state["solver_started"], 2)}}

    def practice(state: TutorState) -> Dict[str, Any]:
        g = state["grounding"]
        label = state["explanation"].misconception or g.misconception_id or ""
        _emit("agent_start", agent="practice")
        t = time.time()
        prefix = f"pr_{uuid.uuid4().hex[:8]}"
        items = []
        try:
            items = p._round_items(state["question"], g, label, state["count"], prefix)
            checks = [p._practice_summary(items)]
        except ModelUnavailable as exc:
            checks = [Check("practice_items_verified", "warn", f"Practice agent failed: {exc}")]
        practice_set = p._practice_set(g, label, items)
        p._open_round(practice_set, prefix, state["question"], state["subject"], label,
                      round_no=1, level="start", history=[])
        _emit("agent_result", agent="practice", data=practice_set)
        return {"label": label, "practice_set": practice_set, "practice_checks": checks,
                "timings": {**state["timings"], "practice": round(time.time() - t, 2)}}

    def reviewer(state: TutorState) -> Dict[str, Any]:
        g, explanation, solution = state["grounding"], state["explanation"], state["solution"]
        _emit("agent_start", agent="reviewer")
        t = time.time()
        checks: List[Check] = (list(state["solution_checks"]) + p.reviewer.check_explanation(g, explanation)
                               + list(state["practice_checks"]))
        verdict, notes = None, ""
        if state["review_with_model"]:
            try:
                crit = p.reviewer.critique(state["question"], explanation, solution, checks)
                verdict, notes = crit["verdict"], crit["notes"]
                if verdict:
                    checks.append(Check("model_review", "warn" if verdict == "FAIL" else "pass",
                                        notes or ("Reviewer model found no problems." if verdict == "PASS"
                                                  else "Reviewer model flagged a concern.")))
            except ModelUnavailable as exc:
                checks.append(Check("model_review", "skip", f"Reviewer model unavailable: {exc}"))
        review = build_review(checks, verdict, notes, state["revisions"], round(time.time() - t, 2))
        _emit("agent_result", agent="reviewer", data=review.to_dict())
        return {"review": review, "timings": {**state["timings"], "reviewer": review.seconds}}

    def finish(state: TutorState) -> Dict[str, Any]:
        from .pipeline import compose_markdown  # pipeline.py imports this module

        g, explanation, review = state["grounding"], state["explanation"], state["review"]
        result = {
            "status": "success",
            "question": state["question"],
            "subject": state["subject"],
            "grounding": g.to_dict(),
            "explanation": explanation.to_dict(),
            "solution": state["solution"].to_dict(),
            "practice_set": state["practice_set"],
            "review": review.to_dict(),
            "misconception": state["label"] or g.misconception_id or "general",
            "model": explanation.model,
            "timings": {**state["timings"], "total": round(time.time() - state["started"], 2)},
        }
        result["answer"] = compose_markdown(result)
        if review.approved:
            p._remember(state["cache_key"], result)
        _emit("complete", result=result)
        return {"result": result}

    # ---- routing ----------------------------------------------------------------------
    def after_explainer(state: TutorState) -> str:
        return END if state.get("stopped") else "solver"

    def after_solver(state: TutorState) -> str:
        if state.get("stopped"):
            return END
        if _failed(state["solution_checks"]) and state["revisions"] < p.max_revisions:
            return "revise"  # an exact check failed: send the issues back to the solver
        return "solved"

    graph = StateGraph(TutorState)
    for name, fn in (("ground", ground), ("explainer", explainer), ("solver", solver), ("revise", revise),
                     ("solved", solved), ("practice", practice), ("reviewer", reviewer), ("finish", finish)):
        graph.add_node(name, fn)
    graph.add_edge(START, "ground")
    graph.add_edge("ground", "explainer")
    graph.add_conditional_edges("explainer", after_explainer, {"solver": "solver", END: END})
    graph.add_conditional_edges("solver", after_solver, {"revise": "revise", "solved": "solved", END: END})
    graph.add_conditional_edges("revise", after_solver, {"revise": "revise", "solved": "solved", END: END})
    graph.add_edge("solved", "practice")
    graph.add_edge("practice", "reviewer")
    graph.add_edge("reviewer", "finish")
    graph.add_edge("finish", END)
    return graph.compile()
