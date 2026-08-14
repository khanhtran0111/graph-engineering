"""Bounded dynamic fan-out using LangGraph ``Send`` instructions."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send


MAX_WORKERS = 5
MAX_DEPTH = 3
ALLOWED_TOOLS = ("search", "catalog")


class DynamicState(TypedDict, total=False):
    discovered_items: list[str]
    planned_items: list[str]
    depth: int
    allowed_tools: tuple[str, ...]
    work_item: str
    worker_results: Annotated[list[tuple[str, str, str]], operator.add]
    fan_out_count: int
    combined: list[str]
    trace: Annotated[list[str], operator.add]
    termination_reason: str


def build_dynamic_graph():
    """Build a graph whose runtime work count is capped by hard policy."""

    def plan(state: DynamicState) -> dict:
        depth = max(0, state.get("depth", 0))
        items = list(dict.fromkeys(state.get("discovered_items", [])))
        planned = items[:MAX_WORKERS] if depth < MAX_DEPTH else []
        allowed = tuple(
            tool for tool in state.get("allowed_tools", ALLOWED_TOOLS) if tool in ALLOWED_TOOLS
        )
        return {
            "planned_items": planned,
            "fan_out_count": len(planned),
            "allowed_tools": allowed or ALLOWED_TOOLS,
            "trace": [f"plan:{len(planned)}"],
        }

    def dispatch(state: DynamicState):
        if not state["planned_items"]:
            return "aggregate"
        return [
            Send(
                "worker",
                {
                    "work_item": item,
                    "depth": state["depth"],
                    "allowed_tools": state["allowed_tools"],
                },
            )
            for item in state["planned_items"]
        ]

    def worker(state: DynamicState) -> dict:
        tool = state["allowed_tools"][0]
        item = state["work_item"]
        return {
            "worker_results": [(item, tool, f"{tool} result for {item}")],
            "trace": [f"worker:{item}:{tool}"],
        }

    def aggregate(state: DynamicState) -> dict:
        ordered = sorted(state.get("worker_results", []))
        return {
            "combined": [result for _, _, result in ordered],
            "termination_reason": (
                "depth_limit_reached" if state.get("depth", 0) >= MAX_DEPTH else "completed"
            ),
            "trace": ["aggregate"],
        }

    builder = StateGraph(DynamicState)
    builder.add_node("plan", plan)
    builder.add_node("worker", worker)
    builder.add_node("aggregate", aggregate)
    builder.add_edge(START, "plan")
    builder.add_conditional_edges("plan", dispatch)
    builder.add_edge("worker", "aggregate")
    builder.add_edge("aggregate", END)
    return builder.compile()
