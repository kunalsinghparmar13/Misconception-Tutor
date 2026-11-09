"""The LangGraph wiring of the four agents (LLM/tutor_agents/graph.py)."""

from test_agents import SOLVE_OK, scripted
from tutor_agents import ModelClient, ModelUnavailable, TutorPipeline

QUESTION = "Why is 1/4 + 1/6 = 1/5 wrong?"
WRONG = "Final answer: 1/5\nSteps:\n1. add across"


def test_graph_has_the_agent_nodes_and_the_revision_loop():
    graph = TutorPipeline(scripted([SOLVE_OK])).graph.get_graph()
    nodes = set(graph.nodes)
    assert {"ground", "explainer", "solver", "revise", "solved", "practice", "reviewer", "finish"} <= nodes
    edges = {(e.source, e.target) for e in graph.edges}
    assert ("solver", "revise") in edges and ("revise", "revise") in edges
    assert ("solved", "practice") in edges and ("reviewer", "finish") in edges


def test_events_reach_the_page_in_the_same_order_as_before():
    events = list(TutorPipeline(scripted([SOLVE_OK]), max_revisions=0).stream(QUESTION, "Mathematics"))
    sequence = [(e["event"], e.get("agent")) for e in events]
    assert sequence == [
        ("start", None),
        ("grounding", None),
        ("agent_start", "explainer"), ("agent_result", "explainer"),
        ("agent_start", "solver"), ("agent_result", "solver"),
        ("agent_start", "practice"), ("agent_result", "practice"),
        ("agent_start", "reviewer"), ("agent_result", "reviewer"),
        ("complete", None),
    ]


def test_the_graph_can_revise_more_than_once():
    events = list(TutorPipeline(scripted([WRONG, WRONG, SOLVE_OK]), max_revisions=2).stream(QUESTION, "Mathematics"))
    assert sum(1 for e in events if e["event"] == "revision") == 2
    result = events[-1]["result"]
    assert result["solution"]["final_answer"] == "5/12"
    assert result["review"]["revisions"] == 2 and result["review"]["approved"] is True


def test_revisions_stop_at_the_limit():
    events = list(TutorPipeline(scripted([WRONG, WRONG, WRONG]), max_revisions=1).stream(QUESTION, "Mathematics"))
    assert sum(1 for e in events if e["event"] == "revision") == 1
    assert events[-1]["result"]["review"]["approved"] is False


def test_model_failure_in_the_explainer_ends_the_graph_early():
    calls = []

    def transport(messages, max_tokens, temperature):
        calls.append(messages[0]["content"][:40])
        raise ModelUnavailable("model is down")

    events = list(TutorPipeline(ModelClient(transport=transport)).stream(QUESTION, "Mathematics"))
    assert events[-1]["event"] == "error" and events[-1]["agent"] == "explainer"
    assert not any(e["event"] == "complete" for e in events)
    assert len(calls) == 1  # the solver, practice and reviewer never ran

