"""Small, framework-light tracing primitives for educational graph runs."""

from __future__ import annotations

import operator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Annotated, Callable, Iterator, TypedDict

from langgraph.graph import END, START, StateGraph


@dataclass(frozen=True)
class NodeEvent:
    node: str
    latency_ms: float
    status: str
    detail: str | None = None
    started_at: float = 0.0
    completed_at: float = 0.0
    attempt: int = 1

    @property
    def duration_ms(self) -> float:
        """Explicit duration name while preserving the original latency field."""

        return self.latency_ms


NodeTrace = NodeEvent


@dataclass(frozen=True)
class GraphMetrics:
    nodes_visited: int
    graph_latency_ms: float
    retries: int
    llm_calls: int
    tool_calls: int
    token_usage: int
    estimated_cost: float
    failures: int


@dataclass
class RunTrace:
    run_id: str
    events: list[NodeEvent] = field(default_factory=list)
    routes: list[str] = field(default_factory=list)
    retries: int = 0
    llm_calls: int = 0
    token_usage: int = 0
    estimated_cost: float = 0.0
    termination_reason: str | None = None
    tool_calls: int = 0
    clock: Callable[[], float] = field(default=perf_counter, repr=False)

    @contextmanager
    def span(self, node: str, attempt: int = 1) -> Iterator[None]:
        """Measure one node and retain only a sanitized error type."""

        started = self.clock()
        status = "ok"
        detail = None
        try:
            yield
        except Exception as error:
            status = "error"
            detail = type(error).__name__
            raise
        finally:
            completed = self.clock()
            self.events.append(
                NodeEvent(
                    node=node,
                    latency_ms=(completed - started) * 1_000,
                    status=status,
                    detail=detail,
                    started_at=started,
                    completed_at=completed,
                    attempt=attempt,
                )
            )

    def record_route(self, route: str) -> None:
        self.routes.append(route)

    def record_retry(self) -> None:
        self.retries += 1

    def record_llm_call(self, tokens: int = 0, estimated_cost: float = 0.0) -> None:
        self.llm_calls += 1
        self.token_usage += tokens
        self.estimated_cost += estimated_cost

    def record_tool_call(self) -> None:
        self.tool_calls += 1

    def finish(self, reason: str) -> None:
        self.termination_reason = reason

    def metrics(self) -> GraphMetrics:
        return GraphMetrics(
            nodes_visited=len(self.events),
            graph_latency_ms=sum(event.latency_ms for event in self.events),
            retries=self.retries,
            llm_calls=self.llm_calls,
            tool_calls=self.tool_calls,
            token_usage=self.token_usage,
            estimated_cost=self.estimated_cost,
            failures=sum(event.status == "error" for event in self.events),
        )

    def summary(self) -> dict:
        return {
            "run_id": self.run_id,
            **asdict(self.metrics()),
            "routes": list(self.routes),
            "termination_reason": self.termination_reason,
            "events": [
                {**asdict(event), "duration_ms": event.duration_ms}
                for event in self.events
            ],
        }

    def render(self) -> str:
        lines = [f"Run: {self.run_id}", "START"]
        lines.extend(
            f"  -> {event.node} (attempt {event.attempt}, "
            f"{event.duration_ms:.2f} ms, {event.status})"
            for event in self.events
        )
        lines.extend(
            [
                "  -> END",
                f"nodes visited: {len(self.events)}",
                f"retries: {self.retries}",
                f"llm calls: {self.llm_calls}",
                f"tool calls: {self.tool_calls}",
                f"termination: {self.termination_reason}",
            ]
        )
        return "\n".join(lines)


ExecutionTrace = RunTrace


class ObservedState(TypedDict, total=False):
    quality_scores: list[float]
    attempt: int
    score: float
    strategy: str
    output: str
    trace: Annotated[list[str], operator.add]
    termination_reason: str


def build_observed_graph(run_trace: RunTrace):
    """Build a deterministic retry graph instrumented with ``RunTrace``."""

    def generate(state: ObservedState) -> dict:
        attempt = state.get("attempt", 0) + 1
        with run_trace.span("generate", attempt):
            run_trace.record_llm_call(tokens=20)
            strategy = state.get("strategy", "baseline")
            return {
                "attempt": attempt,
                "output": f"draft using {strategy}",
                "trace": [f"generate:{attempt}"],
            }

    def evaluate(state: ObservedState) -> dict:
        with run_trace.span("evaluate", state["attempt"]):
            scores = state.get("quality_scores", [1.0])
            score = scores[min(state["attempt"] - 1, len(scores) - 1)]
            return {"score": score, "trace": [f"evaluate:{score:.2f}"]}

    def route(state: ObservedState) -> str:
        selected = "complete" if state["score"] >= 0.8 else "improve"
        run_trace.record_route(selected)
        return selected

    def improve(_: ObservedState) -> dict:
        with run_trace.span("improve"):
            run_trace.record_retry()
            run_trace.record_tool_call()
            return {"strategy": "add_evidence", "trace": ["improve"]}

    def complete(_: ObservedState) -> dict:
        with run_trace.span("complete"):
            run_trace.finish("quality_reached")
            return {
                "termination_reason": "quality_reached",
                "trace": ["complete"],
            }

    builder = StateGraph(ObservedState)
    builder.add_node("generate", generate)
    builder.add_node("evaluate", evaluate)
    builder.add_node("improve", improve)
    builder.add_node("complete", complete)
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "evaluate")
    builder.add_conditional_edges(
        "evaluate", route, {"complete": "complete", "improve": "improve"}
    )
    builder.add_edge("improve", "generate")
    builder.add_edge("complete", END)
    return builder.compile()
