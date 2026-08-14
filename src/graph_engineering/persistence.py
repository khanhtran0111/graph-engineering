"""Checkpoint and idempotency primitives for deterministic demonstrations."""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


class CheckpointState(TypedDict, total=False):
    request: str
    idempotency_key: str
    prepared: str
    evidence: list[str]
    review_packet: str
    action_status: str
    result: str
    visits: Annotated[list[str], operator.add]
    termination_reason: str


@dataclass
class ActionLedger:
    """A tiny stand-in for an idempotent external service."""

    executed_action_ids: set[str] = field(default_factory=set)
    execution_count: int = 0

    def execute_once(self, idempotency_key: str) -> bool:
        """Return True only when this key causes the simulated side effect."""

        if idempotency_key in self.executed_action_ids:
            return False
        self.executed_action_ids.add(idempotency_key)
        self.execution_count += 1
        return True


def thread_config(thread_id: str) -> dict:
    """Build the stable run identity expected by a LangGraph checkpointer."""

    return {"configurable": {"thread_id": thread_id}}


def build_checkpoint_graph(
    ledger: ActionLedger | None = None,
    checkpointer: InMemorySaver | None = None,
):
    """Pause before a protected action and return graph, ledger, and saver."""

    action_ledger = ledger or ActionLedger()
    memory = checkpointer or InMemorySaver()

    def prepare(state: CheckpointState) -> dict:
        return {"prepared": state["request"].strip(), "visits": ["prepare"]}

    def research(state: CheckpointState) -> dict:
        return {
            "evidence": [f"Verified context for: {state['prepared']}"],
            "visits": ["research"],
        }

    def review(state: CheckpointState) -> dict:
        return {
            "review_packet": f"Review {len(state['evidence'])} evidence item(s)",
            "visits": ["review"],
        }

    def protected_action(state: CheckpointState) -> dict:
        executed = action_ledger.execute_once(state["idempotency_key"])
        return {
            "action_status": "executed" if executed else "already_executed",
            "visits": ["protected_action"],
        }

    def finish(state: CheckpointState) -> dict:
        return {
            "result": f"Workflow finished: {state['action_status']}",
            "termination_reason": "completed",
            "visits": ["finish"],
        }

    builder = StateGraph(CheckpointState)
    builder.add_node("prepare", prepare)
    builder.add_node("research", research)
    builder.add_node("review", review)
    builder.add_node("protected_action", protected_action)
    builder.add_node("finish", finish)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "research")
    builder.add_edge("research", "review")
    builder.add_edge("review", "protected_action")
    builder.add_edge("protected_action", "finish")
    builder.add_edge("finish", END)
    graph = builder.compile(
        checkpointer=memory,
        interrupt_before=["protected_action"],
    )
    return graph, action_ledger, memory
