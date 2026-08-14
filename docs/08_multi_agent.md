# Graphs, Agents, and Multi-Agent Systems

An agent is a computational actor. A graph is a control structure. Multi-agent design is an architectural strategy for specialization and communication. They are related, not equivalent.

## Plain LLM

```mermaid
flowchart LR
    accTitle: Plain Language Model Call
    accDescr: A user sends input to one language model and receives one answer without an explicit loop or graph policy.

    user([User]) --> llm[LLM] --> answer([Answer])
```

One semantic computation is enough when no tool use, feedback, branching, or recovery is needed.

## Agent Loop

```mermaid
flowchart LR
    accTitle: Agent Tool Loop
    accDescr: An agent alternates between model reasoning and tool execution until its internal stopping decision ends the loop.

    llm[LLM decision] --> tool[Tool action]
    tool --> observation[Observation]
    observation --> llm
    llm -->|Stop| answer([Answer])
```

An agent loop provides repeated reasoning and action. Its policy may be implicit unless budgets and stop conditions are enforced outside the model.

## Graph

```mermaid
flowchart LR
    accTitle: Explicit Research Graph
    accDescr: A deterministic router selects search or database work, evaluation controls a bounded retry path, and the graph owns termination.

    input([Input]) --> router{Router}
    router --> search[Search]
    router --> database[Database]
    search --> evaluate[Evaluate]
    database --> evaluate
    evaluate --> gate{Quality policy}
    gate -->|Improve and budget remains| router
    gate -->|Finish| answer([Answer])
```

The graph exposes state transitions, routes, and policy. Its nodes can contain zero agents.

## Multi-Agent Graph

```mermaid
flowchart LR
    accTitle: Multi Agent Review Graph
    accDescr: A manager coordinates specialized researcher, analyst, and reviewer actors while a deterministic review policy returns rejected work for bounded revision.

    manager[Manager] --> researcher[Researcher]
    researcher --> analyst[Analyst]
    analyst --> reviewer[Reviewer]
    reviewer --> gate{Review policy}
    gate -->|Revise and budget remains| analyst
    gate -->|Accept| complete([Complete])
    gate -->|Budget exhausted| escalate([Escalate])
```

Here the graph controls collaboration among specialized actors. The agents may themselves use tools or internal loops, but their input/output contracts and the parent graph’s limits remain explicit.

## Choosing the Architecture

| Need | Smallest suitable design |
| --- | --- |
| One transformation | Plain model call or deterministic function |
| Open-ended tool use by one actor | Bounded agent loop |
| Known branches, gates, or recovery policy | Graph |
| Specialization requiring distinct contexts or ownership | Multi-agent graph |

Do not create extra agents for calculators, validators, routers, or retry counters when code is clearer. Multiple prompts with role names do not automatically create useful specialization.

## Common Mistake

A supervisor everywhere becomes a probabilistic router and a bottleneck. Use deterministic edges for known transitions; add semantic coordination only where the choice genuinely requires it.

Next: [Testing graphs](09_testing_graphs.md).
