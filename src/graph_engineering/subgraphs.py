"""Composable graphs with explicit parent/child state contracts."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class ResearchChildState(TypedDict, total=False):
    question: str
    raw_results: list[str]
    validated_results: list[str]
    evidence: list[str]
    validation_notes: str
    status: str


class AnalysisChildState(TypedDict, total=False):
    evidence: list[str]
    draft: str
    score: float
    feedback: str
    attempts: int
    private_scratchpad: str
    status: str


class ReviewChildState(TypedDict, total=False):
    draft: str
    reviewer_note: str
    final_answer: str
    status: str


class ParentState(TypedDict, total=False):
    question: str
    evidence: list[str]
    research_status: str
    draft: str
    analysis_status: str
    final_answer: str
    review_status: str
    trace: Annotated[list[str], operator.add]
    termination_reason: str


def build_research_subgraph():
    def retrieve(state: ResearchChildState) -> dict:
        return {
            "raw_results": [
                f"Primary source about {state['question']}",
                "unverified duplicate",
                "Independent source with a stated limitation",
            ]
        }

    def validate(state: ResearchChildState) -> dict:
        validated = [
            item for item in state["raw_results"] if item != "unverified duplicate"
        ]
        return {
            "validated_results": validated,
            "validation_notes": "Removed one unverified item.",
        }

    def aggregate(state: ResearchChildState) -> dict:
        return {"evidence": state["validated_results"], "status": "validated"}

    builder = StateGraph(ResearchChildState)
    builder.add_node("retrieve", retrieve)
    builder.add_node("validate", validate)
    builder.add_node("aggregate", aggregate)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "validate")
    builder.add_edge("validate", "aggregate")
    builder.add_edge("aggregate", END)
    return builder.compile()


def build_analysis_subgraph():
    def analyze(state: AnalysisChildState) -> dict:
        attempt = state.get("attempts", 0) + 1
        suffix = " with independent-evidence comparison" if attempt > 1 else ""
        return {
            "attempts": attempt,
            "draft": f"Analysis of {len(state['evidence'])} sources{suffix}",
            "private_scratchpad": f"attempt={attempt}",
        }

    def evaluate(state: AnalysisChildState) -> dict:
        score = 0.6 if state["attempts"] == 1 else 0.9
        return {
            "score": score,
            "feedback": "Compare the independent sources." if score < 0.8 else "",
        }

    def route(state: AnalysisChildState) -> str:
        return "improve" if state["score"] < 0.8 and state["attempts"] < 2 else "done"

    def improve(state: AnalysisChildState) -> dict:
        return {"private_scratchpad": f"applied: {state['feedback']}"}

    def done(_: AnalysisChildState) -> dict:
        return {"status": "quality_reached"}

    builder = StateGraph(AnalysisChildState)
    builder.add_node("analyze", analyze)
    builder.add_node("evaluate", evaluate)
    builder.add_node("improve", improve)
    builder.add_node("done", done)
    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "evaluate")
    builder.add_conditional_edges(
        "evaluate", route, {"improve": "improve", "done": "done"}
    )
    builder.add_edge("improve", "analyze")
    builder.add_edge("done", END)
    return builder.compile()


def build_review_subgraph():
    def review(state: ReviewChildState) -> dict:
        return {
            "reviewer_note": "Checked for evidence count and limitation.",
            "final_answer": f"Reviewed: {state['draft']}",
            "status": "approved",
        }

    builder = StateGraph(ReviewChildState)
    builder.add_node("review", review)
    builder.add_edge(START, "review")
    builder.add_edge("review", END)
    return builder.compile()


def build_subgraph_system():
    """Build a parent that maps only documented inputs and outputs."""

    research_graph = build_research_subgraph()
    analysis_graph = build_analysis_subgraph()
    review_graph = build_review_subgraph()

    def research_boundary(state: ParentState) -> dict:
        child = research_graph.invoke({"question": state["question"]})
        return {
            "evidence": child["evidence"],
            "research_status": child["status"],
            "trace": ["research_subgraph"],
        }

    def analysis_boundary(state: ParentState) -> dict:
        child = analysis_graph.invoke({"evidence": state["evidence"]})
        return {
            "draft": child["draft"],
            "analysis_status": child["status"],
            "trace": ["analysis_subgraph"],
        }

    def review_boundary(state: ParentState) -> dict:
        child = review_graph.invoke({"draft": state["draft"]})
        return {
            "final_answer": child["final_answer"],
            "review_status": child["status"],
            "termination_reason": "completed",
            "trace": ["review_subgraph"],
        }

    builder = StateGraph(ParentState)
    builder.add_node("research", research_boundary)
    builder.add_node("analysis", analysis_boundary)
    builder.add_node("review", review_boundary)
    builder.add_edge(START, "research")
    builder.add_edge("research", "analysis")
    builder.add_edge("analysis", "review")
    builder.add_edge("review", END)
    return builder.compile()
