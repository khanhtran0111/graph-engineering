"""Small recovery graph that separates runtime and semantic failures."""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


RuntimeOutcome = Literal["success", "transient", "permanent"]


class RecoveryState(TypedDict, total=False):
    runtime_outcomes: list[RuntimeOutcome]
    quality_scores: list[float]
    max_runtime_retries: int
    max_semantic_attempts: int
    execution_calls: int
    runtime_retries: int
    semantic_attempts: int
    outcome: RuntimeOutcome
    score: float
    strategy: str
    strategy_history: Annotated[list[str], operator.add]
    feedback: str
    artifact: str
    trace: Annotated[list[str], operator.add]
    termination_reason: str


def build_recovery_graph():
    """Build a deterministic graph with distinct recovery policies."""

    def initialize(state: RecoveryState) -> dict:
        strategy = state.get("strategy", "baseline")
        return {
            "execution_calls": 0,
            "runtime_retries": 0,
            "semantic_attempts": 0,
            "strategy": strategy,
            "strategy_history": [strategy],
            "trace": ["initialize"],
        }

    def execute(state: RecoveryState) -> dict:
        call = state.get("execution_calls", 0) + 1
        outcomes = state.get("runtime_outcomes", ["success"])
        outcome = outcomes[call - 1] if call <= len(outcomes) else "success"
        update: dict = {
            "execution_calls": call,
            "outcome": outcome,
            "trace": [f"execute:{call}:{outcome}"],
        }
        if outcome == "success":
            semantic_attempt = state.get("semantic_attempts", 0) + 1
            strategy = state.get("strategy", "baseline")
            update.update(
                {
                    "semantic_attempts": semantic_attempt,
                    "artifact": f"answer using {strategy}",
                }
            )
        return update

    def route_runtime(state: RecoveryState) -> str:
        if state["outcome"] == "success":
            return "evaluate"
        if state["outcome"] == "permanent":
            return "fallback"
        if state.get("runtime_retries", 0) < state.get("max_runtime_retries", 0):
            return "retry"
        return "fallback"

    def retry_runtime(state: RecoveryState) -> dict:
        retry = state.get("runtime_retries", 0) + 1
        return {"runtime_retries": retry, "trace": [f"runtime_retry:{retry}"]}

    def evaluate(state: RecoveryState) -> dict:
        scores = state.get("quality_scores", [1.0])
        attempt = state["semantic_attempts"]
        score = scores[attempt - 1] if attempt <= len(scores) else scores[-1]
        return {"score": score, "trace": [f"evaluate:{score:.2f}"]}

    def route_quality(state: RecoveryState) -> str:
        if state["score"] >= 0.8:
            return "complete"
        if state["semantic_attempts"] >= state.get("max_semantic_attempts", 1):
            return "fallback"
        return "improve"

    def improve(state: RecoveryState) -> dict:
        revised = f"evidence_expansion_{state['semantic_attempts']}"
        return {
            "strategy": revised,
            "strategy_history": [revised],
            "feedback": "Add independent evidence before regenerating.",
            "trace": [f"improve:{revised}"],
        }

    def complete(_: RecoveryState) -> dict:
        return {"termination_reason": "quality_reached", "trace": ["complete"]}

    def fallback(state: RecoveryState) -> dict:
        if state.get("outcome") == "permanent":
            reason = "permanent_failure"
        elif state.get("outcome") == "transient":
            reason = "runtime_retry_budget_exhausted"
        else:
            reason = "semantic_attempt_budget_exhausted"
        return {"termination_reason": reason, "trace": [f"fallback:{reason}"]}

    builder = StateGraph(RecoveryState)
    builder.add_node("initialize", initialize)
    builder.add_node("execute", execute)
    builder.add_node("retry_runtime", retry_runtime)
    builder.add_node("evaluate", evaluate)
    builder.add_node("improve", improve)
    builder.add_node("complete", complete)
    builder.add_node("fallback", fallback)
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "execute")
    builder.add_conditional_edges(
        "execute",
        route_runtime,
        {
            "retry": "retry_runtime",
            "evaluate": "evaluate",
            "fallback": "fallback",
        },
    )
    builder.add_edge("retry_runtime", "execute")
    builder.add_conditional_edges(
        "evaluate",
        route_quality,
        {"complete": "complete", "improve": "improve", "fallback": "fallback"},
    )
    builder.add_edge("improve", "execute")
    builder.add_edge("complete", END)
    builder.add_edge("fallback", END)
    return builder.compile()
