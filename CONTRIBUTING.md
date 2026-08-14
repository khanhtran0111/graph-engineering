# Contributing to Graph Engineering

Contributions are welcome when they make graph architecture easier to understand, run, test, or apply.

## Ways to Contribute

- clarify or correct documentation;
- fix deterministic examples or tests;
- add a graph pattern with a distinct control problem;
- add a notebook that fits the existing concept order;
- extend the research-agent example without skipping prerequisites;
- improve provider isolation, reliability, or observability.

## Development Setup

```bash
uv sync
uv run pytest
uv run jupyter lab
```

The default test suite and deterministic notebooks must run without API credentials. Copy `.env.example` to `.env` only for optional provider-backed experiments. Never commit `.env`, keys, personal prompts, or notebook outputs containing sensitive data.

## Educational Example Standard

A new example should include:

1. **Problem** — the system requirement that justifies the topology.
2. **Topology** — a readable Mermaid diagram with accessible title and description.
3. **State** — fields, ownership, and reducer semantics.
4. **Execution policy** — fixed, conditional, parallel, or paused transitions.
5. **Termination policy** — success, exhausted, failure, and cancellation outcomes.
6. **Tests** — deterministic routing, state, reducer, and termination checks.
7. **README** — how to run it and what to modify.

Examples that only add another prompt do not fit the repository. The educational unit is a graph decision and its engineering consequences.

## Notebook Guidelines

- Introduce concepts before complete code.
- Explain why each code section exists.
- Depend only on earlier notebooks in the learning path.
- Keep provider setup in the shared helper.
- Use deterministic data or fake model responses by default.
- Bound every loop in state and control policy.
- Clear outputs that expose credentials, local paths, or noisy transient results.

Run `uv run python scripts/normalize_notebooks.py` after editing notebooks. Use `--check` to verify normalization without writing.

## Advanced Example Requirements

A persistence example must document its checkpoint boundary, stable run identity, resume behavior, and idempotency policy. Its tests should prove that completed nodes are not needlessly replayed and a simulated side effect executes at most once.

A human-in-the-loop example must use persistent workflow state, identify which deterministic policy requires review, and cover approval, rejection, timeout or escalation policy, and bounded revision where applicable.

A subgraph must define its input and output contract and identify private child state. Test that the parent receives only documented outputs.

A multi-agent example must justify why multiple agents add capabilities beyond functions or subgraphs. Document agent ownership, allow-listed handoffs, fallback, and termination policy.

A dynamic graph must document maximum fan-out, depth, attempts, budget, timeout, tools, and routes. At minimum, test that runtime dispatch cannot exceed its configured bound.

## Pattern Guidelines

Document the problem, mental model, topology, when to use it, when not to use it, state requirements, termination, minimal code, and production considerations. Prefer framework-independent code before optional LangGraph syntax.

## Pull Request Checklist

- [ ] The change has one clear learning objective.
- [ ] Internal links and Mermaid blocks were checked.
- [ ] No key, `.env` value, or machine-specific path was added.
- [ ] Tests do not require a live LLM.
- [ ] Every new cycle has explicit bounded termination.
- [ ] Parallel updates define merge and partial-failure behavior.
- [ ] `uv run pytest` passes.
- [ ] Relevant deterministic notebooks execute end to end.

Keep changes focused. Do not bundle unrelated dependency upgrades or infrastructure into an educational contribution.
