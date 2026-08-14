"""A deliberately small in-memory trace for educational graph runs."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Iterator


@dataclass(frozen=True)
class NodeEvent:
    node: str
    latency_ms: float
    status: str
    detail: str | None = None


@dataclass
class ExecutionTrace:
    run_id: str
    events: list[NodeEvent] = field(default_factory=list)
    routes: list[str] = field(default_factory=list)
    retries: int = 0
    llm_calls: int = 0
    token_usage: int = 0
    estimated_cost: float = 0.0
    termination_reason: str | None = None

    @contextmanager
    def span(self, node: str) -> Iterator[None]:
        """Measure one node and retain only a sanitized status detail."""

        started = perf_counter()
        status = "ok"
        detail = None
        try:
            yield
        except Exception as error:
            status = "error"
            detail = type(error).__name__
            raise
        finally:
            latency_ms = (perf_counter() - started) * 1_000
            self.events.append(NodeEvent(node, latency_ms, status, detail))

    def record_route(self, route: str) -> None:
        self.routes.append(route)

    def record_retry(self) -> None:
        self.retries += 1

    def finish(self, reason: str) -> None:
        self.termination_reason = reason

    def summary(self) -> dict:
        return {
            "run_id": self.run_id,
            "nodes_visited": len(self.events),
            "graph_latency_ms": sum(event.latency_ms for event in self.events),
            "routes": list(self.routes),
            "retries": self.retries,
            "llm_calls": self.llm_calls,
            "token_usage": self.token_usage,
            "estimated_cost": self.estimated_cost,
            "failures": sum(event.status == "error" for event in self.events),
            "termination_reason": self.termination_reason,
            "events": [asdict(event) for event in self.events],
        }
