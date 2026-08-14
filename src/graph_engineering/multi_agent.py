"""Bounded specialist handoffs inside an explicit graph policy."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


ALLOWED_AGENTS = {"research_agent", "analysis_agent", "domain_agent"}
ROLE_TO_AGENT = {
    "research": "research_agent",
    "analysis": "analysis_agent",
    "domain": "domain_agent",
}


class MultiAgentState(TypedDict, total=False):
    task: str
    requested_role: str
    selected_agent: str
    fallback_used: bool
    specialist_output: str
    reviewer_output: str
    review_passed: bool
    force_review_failure: bool
    handoffs: Annotated[list[tuple[str, str]], operator.add]
    termination_reason: str


def build_multi_agent_graph():
    """Build a manager/specialist/reviewer graph with an allow-list."""

    def manager(state: MultiAgentState) -> dict:
        proposed = ROLE_TO_AGENT.get(state.get("requested_role", ""))
        selected = proposed if proposed in ALLOWED_AGENTS else "research_agent"
        return {
            "selected_agent": selected,
            "fallback_used": proposed not in ALLOWED_AGENTS,
            "handoffs": [("manager", selected)],
        }

    def route_specialist(state: MultiAgentState) -> str:
        selected = state["selected_agent"]
        if selected not in ALLOWED_AGENTS:
            raise ValueError(f"Agent is not allowed: {selected}")
        return selected

    def specialist(name: str, capability: str):
        def run(state: MultiAgentState) -> dict:
            return {
                "specialist_output": f"{capability}: {state['task']}",
                "handoffs": [(name, "reviewer")],
            }

        return run

    def reviewer(state: MultiAgentState) -> dict:
        passed = not state.get("force_review_failure", False)
        return {
            "review_passed": passed,
            "reviewer_output": f"Reviewed {state['selected_agent']} output",
            "handoffs": [("reviewer", "quality_gate")],
        }

    def route_quality(state: MultiAgentState) -> str:
        return "complete" if state["review_passed"] else "fallback"

    def complete(_: MultiAgentState) -> dict:
        return {"termination_reason": "quality_reached"}

    def fallback(_: MultiAgentState) -> dict:
        return {"termination_reason": "review_failed_fallback"}

    builder = StateGraph(MultiAgentState)
    builder.add_node("manager", manager)
    builder.add_node(
        "research_agent", specialist("research_agent", "evidence summary")
    )
    builder.add_node(
        "analysis_agent", specialist("analysis_agent", "structured analysis")
    )
    builder.add_node("domain_agent", specialist("domain_agent", "domain check"))
    builder.add_node("reviewer", reviewer)
    builder.add_node("complete", complete)
    builder.add_node("fallback", fallback)
    builder.add_edge(START, "manager")
    builder.add_conditional_edges(
        "manager", route_specialist, {name: name for name in ALLOWED_AGENTS}
    )
    for name in ALLOWED_AGENTS:
        builder.add_edge(name, "reviewer")
    builder.add_conditional_edges(
        "reviewer",
        route_quality,
        {"complete": "complete", "fallback": "fallback"},
    )
    builder.add_edge("complete", END)
    builder.add_edge("fallback", END)
    return builder.compile()
