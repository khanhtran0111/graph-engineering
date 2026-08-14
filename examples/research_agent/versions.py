"""One research system whose topology grows from V0 through V4."""

import operator
from dataclasses import dataclass
from typing import Annotated, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from graph_engineering.control import (
    classify_keywords,
    route_category,
    route_quality,
)

QUALITY_THRESHOLD = 0.8
MAX_ATTEMPTS = 3


class ResearchModel(Protocol):
    """The semantic capabilities required by the example graphs."""

    def classify(self, question: str) -> str: ...

    def answer(
        self,
        question: str,
        evidence: list[str],
        feedback: str = "",
    ) -> str: ...

    def evaluate(self, answer: str, evidence: list[str]) -> tuple[float, str]: ...


@dataclass
class FakeModel:
    """Predictable model stand-in; it keeps graph policy offline and testable."""

    def classify(self, question: str) -> str:
        return classify_keywords(question)

    def answer(
        self,
        question: str,
        evidence: list[str],
        feedback: str = "",
    ) -> str:
        evidence_text = " ".join(evidence) if evidence else "No external evidence."
        revision = f" Revised using: {feedback}" if feedback else ""
        return f"Question: {question} Evidence: {evidence_text}{revision}"

    def evaluate(self, answer: str, evidence: list[str]) -> tuple[float, str]:
        del answer
        score = 0.9 if len(evidence) >= 3 else 0.65
        feedback = (
            "Evidence coverage is sufficient."
            if score >= QUALITY_THRESHOLD
            else "Add one independent source and state the limitation."
        )
        return score, feedback


class ResearchState(TypedDict, total=False):
    question: str
    category: str
    evidence: Annotated[list[str], operator.add]
    source_results: Annotated[list[tuple[str, str]], operator.add]
    analysis: str
    score: float
    feedback: str
    attempts: int
    final_answer: str
    termination_reason: str
    trace: Annotated[list[str], operator.add]


EVIDENCE = {
    "weather": [
        "Heatwaves can increase cooling demand.",
        "Long hot periods can raise peak electricity load.",
    ],
    "trade": [
        "Tariffs change the landed cost of imported goods.",
        "Import volumes can indicate changing market activity.",
    ],
    "politics": [
        "Policy changes can alter business constraints.",
        "Geopolitical events can increase supply-chain risk.",
    ],
}

GENERAL_EVIDENCE = [
    "External conditions can change demand and operating constraints.",
    "A useful conclusion should identify both evidence and limitations.",
]


def run_v0(question: str, model: ResearchModel | None = None) -> str:
    """V0: one question, one semantic computation, no graph."""

    selected_model = model or FakeModel()
    return selected_model.answer(question, [])


def build_v1(model: ResearchModel | None = None):
    """V1: add a fixed research step before answering."""

    selected_model = model or FakeModel()

    def research(_: ResearchState) -> dict:
        return {
            "evidence": GENERAL_EVIDENCE,
            "trace": ["research"],
        }

    def answer(state: ResearchState) -> dict:
        return {
            "final_answer": selected_model.answer(
                state["question"], state.get("evidence", [])
            ),
            "termination_reason": "linear_complete",
            "trace": ["answer"],
        }

    builder = StateGraph(ResearchState)
    builder.add_node("research", research)
    builder.add_node("answer", answer)
    builder.add_edge(START, "research")
    builder.add_edge("research", "answer")
    builder.add_edge("answer", END)
    return builder.compile()


def build_v2(model: ResearchModel | None = None):
    """V2: classify semantically, then route with deterministic policy."""

    selected_model = model or FakeModel()

    def classify(state: ResearchState) -> dict:
        category = selected_model.classify(state["question"])
        return {"category": category, "trace": [f"classify:{category}"]}

    def research_for(category: str):
        def research(_: ResearchState) -> dict:
            return {"evidence": EVIDENCE[category], "trace": [f"research:{category}"]}

        return research

    def answer(state: ResearchState) -> dict:
        return {
            "final_answer": selected_model.answer(
                state["question"], state.get("evidence", [])
            ),
            "termination_reason": "routed_complete",
            "trace": ["answer"],
        }

    builder = StateGraph(ResearchState)
    builder.add_node("classify", classify)
    for category in EVIDENCE:
        builder.add_node(f"{category}_research", research_for(category))
    builder.add_node("answer", answer)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_category,
        {category: f"{category}_research" for category in EVIDENCE},
    )
    for category in EVIDENCE:
        builder.add_edge(f"{category}_research", "answer")
    builder.add_edge("answer", END)
    return builder.compile()


def build_v3(model: ResearchModel | None = None):
    """V3: add evaluation, actionable feedback, and bounded improvement."""

    selected_model = model or FakeModel()

    def research(state: ResearchState) -> dict:
        category = selected_model.classify(state["question"])
        return {
            "category": category,
            "evidence": EVIDENCE[category],
            "trace": [f"research:{category}"],
        }

    def analyze(state: ResearchState) -> dict:
        attempts = state.get("attempts", 0) + 1
        return {
            "analysis": selected_model.answer(
                state["question"],
                state.get("evidence", []),
                state.get("feedback", ""),
            ),
            "attempts": attempts,
            "trace": [f"analyze:{attempts}"],
        }

    def evaluate(state: ResearchState) -> dict:
        score, feedback = selected_model.evaluate(
            state["analysis"], state.get("evidence", [])
        )
        return {
            "score": score,
            "feedback": feedback,
            "trace": [f"evaluate:{score:.2f}"],
        }

    def improve(state: ResearchState) -> dict:
        return {
            "evidence": [
                f"Independent follow-up evidence requested after attempt "
                f"{state['attempts']}."
            ],
            "trace": ["improve:evidence"],
        }

    def route_evaluation(state: ResearchState) -> str:
        return route_quality(
            state,
            threshold=QUALITY_THRESHOLD,
            max_attempts=MAX_ATTEMPTS,
        )

    def complete(state: ResearchState) -> dict:
        return {
            "final_answer": state["analysis"],
            "termination_reason": "quality_reached",
            "trace": ["complete"],
        }

    def fallback(state: ResearchState) -> dict:
        return {
            "final_answer": state["analysis"],
            "termination_reason": "attempt_budget_exhausted",
            "trace": ["fallback"],
        }

    builder = StateGraph(ResearchState)
    builder.add_node("research", research)
    builder.add_node("analyze", analyze)
    builder.add_node("evaluate", evaluate)
    builder.add_node("improve", improve)
    builder.add_node("complete", complete)
    builder.add_node("fallback", fallback)

    builder.add_edge(START, "research")
    builder.add_edge("research", "analyze")
    builder.add_edge("analyze", "evaluate")
    builder.add_conditional_edges(
        "evaluate",
        route_evaluation,
        {
            "complete": "complete",
            "improve": "improve",
            "fallback": "fallback",
        },
    )
    builder.add_edge("improve", "analyze")
    builder.add_edge("complete", END)
    builder.add_edge("fallback", END)
    return builder.compile()


def build_v4(model: ResearchModel | None = None):
    """V4: gather independent evidence in parallel before analysis."""

    selected_model = model or FakeModel()

    def dispatch(_: ResearchState) -> dict:
        return {"trace": ["dispatch"]}

    def source(name: str, evidence: str):
        def collect(_: ResearchState) -> dict:
            return {
                "source_results": [(name, evidence)],
                "trace": [f"source:{name}"],
            }

        return collect

    def aggregate(state: ResearchState) -> dict:
        ordered = sorted(state["source_results"], key=lambda item: item[0])
        return {
            "evidence": [value for _, value in ordered],
            "trace": ["aggregate"],
        }

    def analyze(state: ResearchState) -> dict:
        return {
            "analysis": selected_model.answer(
                state["question"], state.get("evidence", [])
            ),
            "trace": ["analyze"],
        }

    def evaluate(state: ResearchState) -> dict:
        score, feedback = selected_model.evaluate(
            state["analysis"], state.get("evidence", [])
        )
        return {"score": score, "feedback": feedback, "trace": ["evaluate"]}

    def finish(state: ResearchState) -> dict:
        return {
            "final_answer": state["analysis"],
            "termination_reason": "parallel_evaluation_complete",
            "trace": ["complete"],
        }

    sources = {
        "a": "Source A: primary reporting establishes the event.",
        "b": "Source B: sector data provides market context.",
        "c": "Source C: policy material states an important limitation.",
    }

    builder = StateGraph(ResearchState)
    builder.add_node("dispatch", dispatch)
    for name, evidence in sources.items():
        builder.add_node(f"source_{name}", source(name, evidence))
    builder.add_node("aggregate", aggregate)
    builder.add_node("analyze", analyze)
    builder.add_node("evaluate", evaluate)
    builder.add_node("finish", finish)

    builder.add_edge(START, "dispatch")
    for name in sources:
        builder.add_edge("dispatch", f"source_{name}")
    builder.add_edge([f"source_{name}" for name in sources], "aggregate")
    builder.add_edge("aggregate", "analyze")
    builder.add_edge("analyze", "evaluate")
    builder.add_edge("evaluate", "finish")
    builder.add_edge("finish", END)
    return builder.compile()


def build_version(version: int, model: ResearchModel | None = None):
    """Return a compiled graph for versions 1–4."""

    builders = {1: build_v1, 2: build_v2, 3: build_v3, 4: build_v4}
    if version not in builders:
        raise ValueError("Version must be one of 1, 2, 3, or 4.")
    return builders[version](model)
