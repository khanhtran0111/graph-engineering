# Graph Engineering Anti-Patterns

These failure modes hide control, waste model calls, or make execution impossible to bound and test.

## Everything Is an Agent

Do not create LLM actors for deterministic work.

| Avoid | Prefer |
| --- | --- |
| Router agent | Structured category plus code router |
| Validation agent | Schema or deterministic validator |
| Calculator agent | Exact code or trusted tool |
| Retry agent | Counter, error taxonomy, and policy |

Reserve semantic reasoning for LLMs; keep calculations, validation, routing, and hard policy deterministic.

## Infinite Retry

Every cycle needs an explicit success condition and a finite safety condition. Runtime recursion limits are last-resort protection, not business policy.

## Retry Without New Information

Repeating a failed semantic action with identical evidence and strategy is not improvement. Add evaluator feedback, new evidence, revised constraints, or a different strategy—or stop.

## God Node

A node that plans, retrieves, reasons, evaluates, routes, retries, and formats conceals the topology. Split responsibilities where their inputs, outputs, failure policies, or test boundaries differ.

## God State

Do not place every temporary value in global state. Keep fields needed across nodes, routers, checkpoints, or observability boundaries; keep implementation details local.

## LLM-Controlled Deterministic Policy

Do not ask a model, “Should we exceed our retry budget?” Permissions, budgets, deadlines, thresholds, and hard safety rules belong in code. Semantic classification can inform policy but should not silently override it.

## Hidden State Mutation

Mutating the input mapping in place makes updates hard to trace, replay, or merge. Return explicit updates and let the runtime apply reducer semantics.

## Unbounded Context Growth

Appending every message, trace, and tool payload indefinitely increases latency, cost, and exposure. Summarize, compact, externalize, or retain only what later execution needs.

## Supervisor Everywhere

A supervisor is not automatically better architecture. It can add latency, a probabilistic failure point, and an opaque routing bottleneck. Use fixed or conditional edges when the policy is known.

## No Failure Taxonomy

Bad answers, timeouts, rate limits, malformed schemas, and permission denials need different recovery. A single generic failure edge tends to retry permanent errors and mishandle semantic feedback.

## Parallelism Without Merge Semantics

Fan-out without reducer, conflict, synchronization, and partial-failure policy makes results depend on timing. Define all four before adding concurrency.

## Topology for Show

More nodes and agents do not imply a more capable system. Add a node when it creates a meaningful responsibility, state boundary, policy point, parallel opportunity, or observable checkpoint.

Use the [checklist](graph_engineering_checklist.md) during design and review.
