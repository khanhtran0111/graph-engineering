"""Deterministic fan-out/fan-in helpers used by lessons and tests."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


SourceResult = tuple[str, str]


def merge_source_results(
    current: list[SourceResult], incoming: list[SourceResult]
) -> list[SourceResult]:
    """Merge branch results without discarding updates from another branch."""

    return [*current, *incoming]


class ParallelState(TypedDict, total=False):
    question: str
    source_results: Annotated[list[SourceResult], merge_source_results]
    source_errors: Annotated[list[str], operator.add]
    evidence: list[str]
    trace: Annotated[list[str], operator.add]
    termination_reason: str


SOURCES = {
    "climate": "Heat events increase cooling demand.",
    "market": "Cooling-product sales track sustained hot periods.",
    "grid": "Peak electricity load is a constraint on cooling demand.",
}


def build_parallel_graph(failing_sources: set[str] | None = None):
    """Build a graph whose fan-in retains successes after partial failure."""

    failures = set(failing_sources or ())

    def dispatch(_: ParallelState) -> dict:
        return {"trace": ["dispatch"]}

    def source(name: str, evidence: str):
        def collect(_: ParallelState) -> dict:
            if name in failures:
                return {
                    "source_errors": [name],
                    "trace": [f"source:{name}:failed"],
                }
            return {
                "source_results": [(name, evidence)],
                "trace": [f"source:{name}:ok"],
            }

        return collect

    def aggregate(state: ParallelState) -> dict:
        ordered = sorted(state.get("source_results", []))
        errors = state.get("source_errors", [])
        return {
            "evidence": [value for _, value in ordered],
            "termination_reason": (
                "partial_success" if errors else "all_sources_succeeded"
            ),
            "trace": ["aggregate"],
        }

    builder = StateGraph(ParallelState)
    builder.add_node("dispatch", dispatch)
    for name, evidence in SOURCES.items():
        builder.add_node(f"source_{name}", source(name, evidence))
    builder.add_node("aggregate", aggregate)

    builder.add_edge(START, "dispatch")
    for name in SOURCES:
        builder.add_edge("dispatch", f"source_{name}")
    builder.add_edge([f"source_{name}" for name in SOURCES], "aggregate")
    builder.add_edge("aggregate", END)
    return builder.compile()
