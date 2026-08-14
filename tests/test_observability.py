import pytest

from graph_engineering.observability import RunTrace, build_observed_graph


class StepClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.001
        return self.value


def test_trace_records_graph_execution_policy():
    trace = RunTrace("trace-test", clock=StepClock())
    result = build_observed_graph(trace).invoke(
        {"quality_scores": [0.5, 0.9], "trace": []}
    )
    summary = trace.summary()

    assert result["termination_reason"] == "quality_reached"
    assert summary["nodes_visited"] == 6
    assert summary["routes"] == ["improve", "complete"]
    assert summary["retries"] == 1
    assert summary["llm_calls"] == 2
    assert summary["tool_calls"] == 1
    assert summary["termination_reason"] == "quality_reached"
    assert all(
        event["duration_ms"] == pytest.approx(1.0) for event in summary["events"]
    )
