"""Persistent human-review graph using LangGraph's explicit interrupt API."""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


MAX_REVISIONS = 1
Decision = Literal["approve", "reject", "revise"]


class HumanLoopState(TypedDict, total=False):
    request: str
    risk_level: str
    proposal: str
    requires_approval: bool
    decision: Decision
    requested_changes: str
    revisions: int
    action_executed: bool
    termination_reason: str
    trace: Annotated[list[str], operator.add]


def human_thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def build_human_loop_graph(checkpointer: InMemorySaver | None = None):
    """Build a graph where deterministic risk policy owns the approval gate."""

    memory = checkpointer or InMemorySaver()

    def generate(state: HumanLoopState) -> dict:
        revision = state.get("revisions", 0)
        suffix = (
            f"; revised with: {state.get('requested_changes', 'review feedback')}"
            if revision
            else ""
        )
        return {
            "proposal": f"Proposal for {state['request']}{suffix}",
            "trace": [f"generate:{revision}"],
        }

    def evaluate_risk(state: HumanLoopState) -> dict:
        requires_approval = state.get("risk_level") == "high"
        return {
            "requires_approval": requires_approval,
            "trace": [f"risk:{state.get('risk_level', 'unknown')}"],
        }

    def route_risk(state: HumanLoopState) -> str:
        return "human_review" if state["requires_approval"] else "execute"

    def human_review(state: HumanLoopState) -> dict:
        response = interrupt(
            {
                "proposal": state["proposal"],
                "risk_level": state["risk_level"],
                "allowed_decisions": ["approve", "reject", "revise"],
            }
        )
        if isinstance(response, str):
            decision = response
            changes = ""
        else:
            decision = response.get("decision", "reject")
            changes = response.get("requested_changes", "")
        return {
            "decision": decision,
            "requested_changes": changes,
            "trace": [f"human:{decision}"],
        }

    def route_decision(state: HumanLoopState) -> str:
        if state.get("decision") == "approve":
            return "execute"
        if (
            state.get("decision") == "revise"
            and state.get("revisions", 0) < MAX_REVISIONS
        ):
            return "revise"
        return "stop"

    def revise(state: HumanLoopState) -> dict:
        revision = state.get("revisions", 0) + 1
        return {"revisions": revision, "trace": [f"revise:{revision}"]}

    def execute(_: HumanLoopState) -> dict:
        return {
            "action_executed": True,
            "termination_reason": "approved_and_executed",
            "trace": ["execute"],
        }

    def stop(state: HumanLoopState) -> dict:
        reason = (
            "revision_budget_exhausted"
            if state.get("decision") == "revise"
            else "human_rejected"
        )
        return {
            "action_executed": False,
            "termination_reason": reason,
            "trace": [f"stop:{reason}"],
        }

    builder = StateGraph(HumanLoopState)
    builder.add_node("generate", generate)
    builder.add_node("evaluate_risk", evaluate_risk)
    builder.add_node("human_review", human_review)
    builder.add_node("revise", revise)
    builder.add_node("execute", execute)
    builder.add_node("stop", stop)
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "evaluate_risk")
    builder.add_conditional_edges(
        "evaluate_risk",
        route_risk,
        {"human_review": "human_review", "execute": "execute"},
    )
    builder.add_conditional_edges(
        "human_review",
        route_decision,
        {"execute": "execute", "revise": "revise", "stop": "stop"},
    )
    builder.add_edge("revise", "generate")
    builder.add_edge("execute", END)
    builder.add_edge("stop", END)
    return builder.compile(checkpointer=memory), memory
