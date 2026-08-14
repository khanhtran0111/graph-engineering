# Observability

Graph observability answers not only “what was returned?” but also “which path ran, why did it run, how much did it cost, and why did it stop?”

## A Useful Run Trace

```text
RUN #42

START
 ↓
classify          120 ms
 ↓
research          340 ms
 ↓
analyze           810 ms
 ↓
evaluate          430 ms
 ↓
improve           250 ms
 ↓
evaluate          410 ms
 ↓
END

nodes visited:    6
LLM calls:        4
retries:          1
latency:          2.36 s
final score:      0.91
termination:      quality_reached
```

The exact format is less important than stable event fields and a run identifier that connects them.

## Metrics to Expose

| Metric | What it reveals |
| --- | --- |
| Graph latency | End-to-end user cost |
| Node latency | Slow steps and dependency bottlenecks |
| Node visit count | Unexpected cycles or hot paths |
| Retry count | Dependency instability or weak recovery |
| Route distribution | Classifier drift and workload mix |
| LLM calls and token usage | Resource consumption |
| Estimated cost | Budget pressure by route or tenant |
| Failure count by class | Where reliability work is needed |
| Termination reason | Whether runs succeed, degrade, or exhaust policy |

## Event Model

A lightweight event can be enough:

```python
{
    "run_id": "42",
    "node": "evaluate",
    "route": "improve",
    "latency_ms": 430.2,
    "status": "ok",
    "attempt": 1,
}
```

Capture node start and finish, the fields changed rather than entire sensitive values, router decisions, failure classification, budget state, and termination. The small trace helper in [`src/graph_engineering/observability.py`](../src/graph_engineering/observability.py) demonstrates this without an observability platform.

## State, Logs, and Checkpoints

These serve different purposes:

- state drives the current execution;
- a checkpoint allows persistence or resumption;
- a trace explains events across the run;
- metrics aggregate behavior across many runs.

Do not place every log event in graph state. Large traces can live in a logging sink while state retains only route history or fields needed by later policy.

## Privacy and Safety

Redact credentials, personal data, tool secrets, and sensitive prompts. Define access and retention. Prefer field names, hashes, sizes, or summaries when complete values are unnecessary for diagnosis.

## Common Mistake

Logging only the final response makes routing, retries, and exhausted budgets invisible. Logging every state value creates a different failure: uncontrolled data exposure and volume. Design the event schema deliberately.

Next: [Graphs and multi-agent systems](08_multi_agent.md).
