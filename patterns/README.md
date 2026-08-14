# Graph Engineering Pattern Library

Patterns are reusable execution topologies. They describe state and control decisions first; a framework supplies the runtime syntax afterward.

| Pattern | Primary problem | Characteristic control |
| --- | --- | --- |
| [Router](#router) | Select one strategy at runtime | Conditional edge |
| [Evaluator–Optimizer](#evaluatoroptimizer) | Improve work until acceptable | Quality gate and bounded loop |
| [Retry with Feedback](#retry-with-feedback) | Recover by changing a failed strategy | Error analysis and bounded loop |
| [Fan-Out/Fan-In](#fan-outfan-in) | Run independent work concurrently | Parallel edges, reducer, synchronization |
| [Human Gate](#human-gate) | Require accountable approval | Pause, decision, revision, or execution |

## Router

### Problem

The next execution strategy depends on runtime state, such as topic, request type, risk, or capability.

### Mental model

A classifier computes a structured fact. A router validates that fact and selects a known edge.

```mermaid
flowchart LR
    accTitle: Router Pattern
    accDescr: Input is classified and a deterministic router selects exactly one of three known execution branches.

    input([Input]) --> classify[Classify]
    classify --> router{Router}
    router -->|a| branch_a[Branch A]
    router -->|b| branch_b[Branch B]
    router -->|c| branch_c[Branch C]
```

### When to use

Use a router when branches have meaningfully different computation, tools, cost, risk, or state requirements.

### When not to use

Do not add routing when all paths perform the same work, or when a direct function call expresses a trivial implementation detail more clearly.

### State requirements

Store the validated routing field, optional confidence or reason, and a trace entry. Define an `unknown` or invalid-category policy.

### Termination considerations

A one-way router has no cycle. If a branch returns to classification, bound reclassification attempts and require a state change.

### Minimal code example

```python
ALLOWED = {"weather", "trade", "politics"}

def classify(state: dict) -> dict:
    text = state["question"].lower()
    category = "weather" if "rain" in text else "trade" if "tariff" in text else "politics"
    return {"category": category}

def route(state: dict) -> str:
    category = state["category"]
    if category not in ALLOWED:
        raise ValueError(f"Unsupported category: {category}")
    return category
```

### Production considerations

Track route distribution and invalid outputs. Validate LLM-produced categories against a schema. Apply permissions, budgets, and safety constraints after semantic classification in deterministic code.

## Evaluator–Optimizer

### Problem

One generation pass may not meet a measurable quality standard.

### Mental model

Generation produces work, evaluation produces assessment data, and a policy decides whether to complete, improve, or stop at the budget.

```mermaid
flowchart LR
    accTitle: Evaluator Optimizer Pattern
    accDescr: Generated work is evaluated, accepted when it meets policy, or improved with feedback until an explicit attempt limit is reached.

    generate[Generate] --> evaluate[Evaluate]
    evaluate --> gate{Quality policy}
    gate -->|Pass| complete([Complete])
    gate -->|Fail and budget remains| improve[Improve strategy]
    improve --> generate
    gate -->|Budget exhausted| fallback([Fallback])
```

### When to use

Use it when evaluation criteria are meaningful and another iteration can use feedback to improve the result.

### When not to use

Do not loop when evaluation is unreliable, the task is low-value, latency is strict, or the optimizer cannot act on the feedback.

### State requirements

Keep the current artifact, score or validation result, actionable feedback, attempt count, quality threshold, and termination reason. Compact older drafts unless the application needs them.

### Termination considerations

Terminate on quality success and on a maximum attempt, deadline, token, or cost bound. Define whether exhaustion accepts the best result, uses a fallback, or escalates.

### Minimal code example

```python
QUALITY_THRESHOLD = 0.8
MAX_ATTEMPTS = 3

def quality_route(state: dict) -> str:
    if state["score"] >= QUALITY_THRESHOLD:
        return "complete"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "fallback"
    return "improve"
```

### Production considerations

Version evaluator criteria, record score distributions and attempt counts, avoid evaluator/optimizer prompt coupling, and reserve a runtime guard above the business limit.

## Retry with Feedback

### Problem

Execution failed in a way that may be recoverable only after the error is understood and the strategy changes.

### Mental model

The loop is not “run again.” It is “classify the failure, derive an actionable change, then execute under a remaining budget.”

```mermaid
flowchart TD
    accTitle: Retry With Feedback Pattern
    accDescr: Execution either completes or sends a failure to analysis, where strategy is modified before a bounded retry.

    execute[Execute] --> failed{Failure?}
    failed -->|No| complete([Complete])
    failed -->|Yes and recoverable| analyze[Analyze error]
    analyze --> modify[Modify strategy]
    modify --> execute
    failed -->|Permanent or exhausted| fallback([Fallback or stop])
```

### When to use

Use it for semantic failures or structured runtime failures where the next action can change tool, arguments, evidence, format, or execution plan.

### When not to use

Do not retry permanent permission failures, deterministic bugs, or identical semantic requests with no new information.

### State requirements

Store a failure class, sanitized error details, attempt count, revised strategy, and the last successful checkpoint or artifact when relevant.

### Termination considerations

Use separate retry budgets for semantic and runtime failures. Stop on permanent failure, exhausted budget, deadline, cancellation, or a successful execution.

### Minimal code example

```python
def failure_route(state: dict) -> str:
    if state.get("status") == "ok":
        return "complete"
    if state.get("failure_kind") == "permanent":
        return "fallback"
    if state.get("attempts", 0) >= state["max_attempts"]:
        return "fallback"
    return "analyze_error"
```

### Production considerations

Use backoff and jitter only for suitable transient failures, honor provider retry guidance, redact error payloads, make side effects idempotent, and measure recovery rate by failure class.

## Fan-Out/Fan-In

### Problem

Several independent tasks can begin from the same state and their results are needed together downstream.

### Mental model

Fan-out creates concurrent branches. Reducers merge compatible updates. Fan-in is a synchronization and partial-failure policy boundary.

```mermaid
flowchart LR
    accTitle: Fan Out Fan In Pattern
    accDescr: Input starts three independent workers whose updates synchronize at one aggregation step.

    input([Input]) --> worker_a[Worker A]
    input --> worker_b[Worker B]
    input --> worker_c[Worker C]
    worker_a --> aggregate[Aggregate]
    worker_b --> aggregate
    worker_c --> aggregate
    aggregate --> complete([Complete])
```

### When to use

Use it when tasks have no dependency on one another and concurrency can reduce latency or improve coverage.

### When not to use

Do not parallelize dependent tasks, conflicting side effects, or work whose resource pressure outweighs latency benefit.

### State requirements

Use reducers with explicit identity, ordering, duplication, and conflict behavior. Record source status as well as output.

### Termination considerations

Define whether fan-in requires all branches, a quorum, or any success. Bound each branch and the overall deadline; decide what aggregation does with missing results.

### Minimal code example

```python
def worker(source: str, query: str) -> dict:
    return {"results": [(source, lookup(source, query))]}

def aggregate(state: dict) -> dict:
    ordered = sorted(state["results"], key=lambda item: item[0])
    return {"evidence": [value for _, value in ordered]}
```

### Production considerations

Limit concurrency, propagate cancellation, use per-branch timeouts, avoid unsafe last-writer-wins updates, and trace which branches contributed to the final result.

## Human Gate

### Problem

An action requires accountable review because it is high-impact, irreversible, ambiguous, or governed by policy.

### Mental model

The graph prepares a review packet, persists state, waits for a structured decision, and follows approve, revise, reject, or timeout policy.

```mermaid
flowchart TD
    accTitle: Human Gate Pattern
    accDescr: Generated work pauses for human review and either executes after approval, returns for bounded revision, or terminates on rejection or timeout.

    generate[Generate proposal] --> review[Human review]
    review --> decision{Decision}
    decision -->|Approve| execute[Execute action]
    decision -->|Request changes| revise[Revise proposal]
    revise --> generate
    decision -->|Reject or timeout| stop([Stop or escalate])
    execute --> complete([Complete])
```

### When to use

Use it for destructive actions, financial or legal impact, publication, sensitive communications, production changes, or low-confidence cases where policy requires a person.

### When not to use

Do not add manual review to every low-risk step. It increases latency and can create review fatigue without improving safety.

### State requirements

Persist the proposal, evidence, risk summary, reviewer decision, requested changes, actor identity, timestamps, and idempotency key for the approved action.

### Termination considerations

Bound revision cycles. Define review timeout, rejection, cancellation, reassignment, and escalation behavior. Approval must not erase other budgets or permissions.

### Minimal code example

```python
def approval_route(state: dict) -> str:
    decision = state["review"]["decision"]
    if decision == "approve":
        return "execute"
    if decision == "revise" and state["revisions"] < state["max_revisions"]:
        return "revise"
    return "stop"
```

### Production considerations

Use durable checkpoints, authenticated reviewers, audit history, least-privilege execution, stale-approval checks, and idempotent actions. A human gate is a policy boundary, not a decorative node.

## Selecting a Pattern

Combine patterns only when requirements demand it. For example, parallel research may feed an evaluator–optimizer, which may require a human gate before publication. At each composition boundary, reconcile state contracts and ensure the combined graph still has a finite termination path.

Use the [Graph Engineering checklist](../docs/graph_engineering_checklist.md) to review the result.
