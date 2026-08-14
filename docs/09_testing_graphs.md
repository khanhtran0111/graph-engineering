# Testing Graphs

Graph control logic must be testable independently of model intelligence. Most correctness properties concern state, routes, budgets, and termination—not prose quality.

## Test Layers

| Layer | Test target | Model required? |
| --- | --- | --- |
| Node unit | Input state → explicit update | Usually no |
| Router unit | State → named route | No |
| Reducer | Several updates → merged value | No |
| Subgraph | Known input → path and output | Fake or deterministic model |
| Termination | Loop stops at success or bound | No |
| Provider contract | Client parsing and error mapping | Mocked response |
| End-to-end quality | Real model behavior | Optional, separate, and non-deterministic |

## Pure Router Test

```python
def test_router_selects_expected_branch():
    assert route_category({"category": "weather"}) == "weather"
    assert route_category({"category": "trade"}) == "trade"
```

Use parameterized tests to cover all named routes and invalid structured values.

## Bounded Loop Test

```python
def test_retry_budget_is_respected():
    result = graph.invoke({"attempts": 0, "score": 0.0, "trace": []})
    assert result["attempts"] <= MAX_ATTEMPTS
    assert result["termination_reason"] in {
        "quality_reached",
        "attempt_budget_exhausted",
    }
```

Test both success before the limit and persistent failure at the limit. A runtime recursion error should fail the test; it is not a valid business outcome.

## Fake Models

A fake model should return a sequence or response based on explicit input:

```python
class FakeEvaluator:
    def __init__(self, scores: list[float]):
        self._scores = iter(scores)

    def evaluate(self, _: str) -> float:
        return next(self._scores)
```

Fakes make routes reproducible and permit assertions on call counts. Keep live-model evaluations outside the default test suite so local development and CI do not need credentials.

## Invariants Worth Testing

- nodes do not mutate their input mapping;
- route names match compiled conditional edges;
- every cycle advances a counter, deadline, or monotonic condition;
- reducers preserve all expected parallel contributions;
- exhausted retries select fallback or termination;
- the trace records the chosen path and final reason;
- provider absence produces a clear configuration error.

The repository’s [`tests`](../tests/) demonstrate these checks with deterministic functions.

## Common Mistake

Snapshotting only the final text cannot reveal a wrong route that happened to produce plausible prose. Assert state transitions, visit counts, routes, and termination reason.

Next: [Evaluating Graph Systems](10_evaluating_graph_systems.md), [Anti-patterns](anti_patterns.md), and the [Graph Engineering checklist](graph_engineering_checklist.md).
