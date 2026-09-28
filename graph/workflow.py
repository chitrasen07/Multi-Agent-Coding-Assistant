from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from agents.architect import architect
from agents.planner import planner


class AgentState(TypedDict, total=False):
    user_request: str
    project_type: str
    features: list[str]
    technical_requirements: list[str]
    implementation_steps: list[str]
    project_name: str
    folders: list[str]
    files: list[dict[str, str]]


def build_workflow():
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner)
    graph.add_node("architect", architect)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "architect")
    graph.add_edge("architect", END)
    return graph.compile()


workflow = build_workflow()


def run(user_request: str) -> AgentState:
    return workflow.invoke({"user_request": user_request})
