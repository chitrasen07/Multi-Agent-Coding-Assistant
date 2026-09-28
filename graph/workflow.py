from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from agents.architect import architect
from agents.coder import coder
from agents.fixer import fixer
from agents.planner import planner
from agents.reviewer import reviewer

MAX_FIX_CYCLES = 2


class AgentState(TypedDict, total=False):
    user_request: str
    plan: dict
    architecture: dict
    project_path: str
    generated_files: list[dict[str, str]]
    review: dict
    fix_cycles: int
    fix_status: str


def _route_review(state: AgentState) -> str:
    if state["review"]["status"] == "PASS":
        return "complete"
    if state.get("fix_cycles", 0) >= MAX_FIX_CYCLES:
        return "complete"
    return "fixer"


def build_workflow():
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner)
    graph.add_node("architect", architect)
    graph.add_node("coder", coder)
    graph.add_node("reviewer", reviewer)
    graph.add_node("fixer", fixer)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "architect")
    graph.add_edge("architect", "coder")
    graph.add_edge("coder", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        _route_review,
        {"complete": END, "fixer": "fixer"},
    )
    graph.add_edge("fixer", "reviewer")
    return graph.compile()


workflow = build_workflow()


def run(user_request: str) -> AgentState:
    return workflow.invoke({"user_request": user_request})
