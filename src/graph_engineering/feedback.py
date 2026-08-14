"""A bounded evaluator-optimizer graph with injectable deterministic scoring."""

import operator
from collections.abc import Callable
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from graph_engineering.control import route_quality

QUALITY_THRESHOLD = 0.8
MAX_ATTEMPTS = 3


class FeedbackState(TypedDict, total=False):
    topic: str
    draft: str
    score: float
    feedback: str
    strategy: str
    attempts: int
    final_answer: str
    termination_reason: str
    trace: Annotated[list[str], operator.add]


ScoreFunction = Callable[[FeedbackState], float]


def generate(state: FeedbackState) -> dict:
    """Generate a deterministic draft that responds to the current strategy."""

    attempts = state.get("attempts", 0) + 1
    strategy = state.get("strategy", "state the main claim")
    draft = f"Draft {attempts} about {state['topic']}: {strategy}."
    return {
        "attempts": attempts,
        "draft": draft,
        "trace": [f"generate:{attempts}"],
    }


def default_score(state: FeedbackState) -> float:
    """Increase predictably after feedback so the lesson is reproducible."""

    return min(0.45 + 0.2 * state.get("attempts", 0), 0.95)


def make_evaluator(score_fn: ScoreFunction) -> Callable[[FeedbackState], dict]:
    """Create an evaluator node around an injectable scoring function."""

    def evaluate(state: FeedbackState) -> dict:
        score = max(0.0, min(1.0, float(score_fn(state))))
        feedback = (
            "Quality target reached."
            if score >= QUALITY_THRESHOLD
            else "Add a concrete limitation and supporting detail."
        )
        return {
            "score": score,
            "feedback": feedback,
            "trace": [f"evaluate:{score:.2f}"],
        }

    return evaluate


def improve(state: FeedbackState) -> dict:
    """Turn evaluator feedback into a changed generation strategy."""

    return {
        "strategy": f"revise using feedback: {state['feedback']}",
        "trace": ["improve"],
    }


def quality_route(state: FeedbackState) -> str:
    """Apply the graph's business termination policy."""

    return route_quality(
        state,
        threshold=QUALITY_THRESHOLD,
        max_attempts=MAX_ATTEMPTS,
    )


def complete(state: FeedbackState) -> dict:
    return {
        "final_answer": state["draft"],
        "termination_reason": "quality_reached",
        "trace": ["complete"],
    }


def fallback(state: FeedbackState) -> dict:
    return {
        "final_answer": state["draft"],
        "termination_reason": "attempt_budget_exhausted",
        "trace": ["fallback"],
    }


def build_feedback_graph(score_fn: ScoreFunction = default_score):
    """Compile a loop that always ends by success or an attempt bound."""

    builder = StateGraph(FeedbackState)
    builder.add_node("generate", generate)
    builder.add_node("evaluate", make_evaluator(score_fn))
    builder.add_node("improve", improve)
    builder.add_node("complete", complete)
    builder.add_node("fallback", fallback)

    builder.add_edge(START, "generate")
    builder.add_edge("generate", "evaluate")
    builder.add_conditional_edges(
        "evaluate",
        quality_route,
        {
            "complete": "complete",
            "improve": "improve",
            "fallback": "fallback",
        },
    )
    builder.add_edge("improve", "generate")
    builder.add_edge("complete", END)
    builder.add_edge("fallback", END)
    return builder.compile()
