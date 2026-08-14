"""A deterministic graph used by the first notebook and the test suite."""

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class NumberState(TypedDict, total=False):
    """State shared by the deterministic number graph."""

    value: int
    category: Literal["even", "odd"]
    result: int
    trace: Annotated[list[str], operator.add]


def classify_number(state: NumberState) -> dict:
    """Compute parity without mutating the input state."""

    category: Literal["even", "odd"] = (
        "even" if state["value"] % 2 == 0 else "odd"
    )
    return {"category": category, "trace": [f"classify:{category}"]}


def route_number(state: NumberState) -> Literal["even", "odd"]:
    """Select a branch from a category already computed by a node."""

    category = state["category"]
    if category not in {"even", "odd"}:
        raise ValueError(f"Unsupported number category: {category!r}")
    return category


def multiply(state: NumberState) -> dict:
    """Double even values."""

    return {"result": state["value"] * 2, "trace": ["multiply"]}


def add(state: NumberState) -> dict:
    """Add three to odd values."""

    return {"result": state["value"] + 3, "trace": ["add"]}


def build_number_graph():
    """Compile the no-LLM graph used throughout the fundamentals lesson."""

    builder = StateGraph(NumberState)
    builder.add_node("classify", classify_number)
    builder.add_node("multiply", multiply)
    builder.add_node("add", add)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_number,
        {"even": "multiply", "odd": "add"},
    )
    builder.add_edge("multiply", END)
    builder.add_edge("add", END)
    return builder.compile()
