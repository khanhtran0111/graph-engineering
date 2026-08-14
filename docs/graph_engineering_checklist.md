# Graph Engineering Checklist

Use this checklist before implementing a graph and again during review.

## State

- [ ] Are state fields explicitly defined and typed where practical?
- [ ] Is each field needed across nodes, routers, checkpoints, or trace boundaries?
- [ ] Are reducer semantics explicit?
- [ ] Can parallel updates conflict or arrive in nondeterministic order?
- [ ] Are sensitive and large values handled deliberately?

## Nodes

- [ ] Does each node have one clear responsibility?
- [ ] Is deterministic work implemented deterministically?
- [ ] Does the node return an explicit update instead of mutating input state?
- [ ] Are side effects visible, idempotent where needed, and safe to retry?

## Routing

- [ ] Are route names and decisions understandable from code?
- [ ] Are deterministic policies handled in code?
- [ ] Are semantic classifications validated before routing?
- [ ] Can every route be unit tested without a live LLM?

## Loops

- [ ] Does every loop have a success condition and a finite safety condition?
- [ ] Is retry bounded by attempts, time, budget, or another monotonic limit?
- [ ] Does a failed semantic iteration introduce new information or strategy?
- [ ] Is the exhausted path explicit?

## Reliability

- [ ] Are semantic, transient runtime, permanent, and contract failures separated?
- [ ] Are timeout, backoff, retry, fallback, cancellation, and deadline policies defined where relevant?
- [ ] Are token and cost budgets enforced outside probabilistic components?
- [ ] Is degraded behavior identified rather than reported as full success?

## Parallelism

- [ ] Are parallel tasks actually independent?
- [ ] Does fan-in wait for the intended set or quorum?
- [ ] Is merge behavior safe and order-aware?
- [ ] Is partial failure handled and recorded?

## Observability

- [ ] Can the execution route be reconstructed by run identifier?
- [ ] Are node and graph latency measurable?
- [ ] Are retries, failures, usage, and route decisions recorded?
- [ ] Is termination reason explicit?
- [ ] Are secrets and sensitive data redacted?

## Persistence and Human Review

- [ ] Is run or thread identity stable across pause and resume?
- [ ] Are checkpoint boundaries and resume behavior explicit?
- [ ] Are side effects idempotent across retry, replay, and new runs?
- [ ] Does deterministic policy decide when approval is mandatory?
- [ ] Are rejection, timeout, escalation, and revision bounds defined?

## Subgraphs, Agents, and Dynamic Work

- [ ] Do child graphs expose intentional input and output contracts?
- [ ] Are private child fields isolated from parent state?
- [ ] Is every agent justified by distinct capability or context?
- [ ] Are agent and tool routes allow-listed by graph policy?
- [ ] Are dynamic fan-out, depth, attempts, time, and cost bounded?

## Testing

- [ ] Can nodes be tested independently?
- [ ] Can reducers and routing be tested without an LLM?
- [ ] Can termination be verified deterministically?
- [ ] Do tests cover exhausted budgets and fallback paths?
- [ ] Are live-model evaluations separate from the default suite?

## Production Review

- [ ] Are checkpoint boundaries and resume behavior defined if execution is long-running?
- [ ] Can retried side effects be deduplicated?
- [ ] Are provider-specific details isolated from graph policy?
- [ ] Does topology complexity correspond to a stated system requirement?
