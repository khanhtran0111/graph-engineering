# Graph Engineering

This repository focuses on Graph Engineering for AI agents: designing structured, stateful workflows that can branch, loop, evaluate, recover, and terminate under explicit conditions.

Here, a graph is not a data structure for algorithms such as DFS, BFS, or shortest-path search. It represents the workflow and orchestration of an AI system, where:

- A **node** performs computation.
- **State** stores shared working data.
- An **edge** describes execution flow.
- A **router** selects the next branch.
- A **policy** controls retries, fallbacks, and termination.

> **Graph Engineering is the practice of designing stateful control flow for an AI system.**

## Table of Contents

- [Why Graph Engineering?](#why-graph-engineering)
- [Core Mental Model](#core-mental-model)
- [The Graph as a Control Plane](#the-graph-as-a-control-plane)
- [Loops, Feedback, and Termination](#loops-feedback-and-termination)
- [Graph Engineering and Multi-Agent Systems](#graph-engineering-and-multi-agent-systems)
- [Essential Execution Patterns](#essential-execution-patterns)
- [Reliability and Observability](#reliability-and-observability)
- [Reference Production Architecture](#reference-production-architecture)

## Why Graph Engineering?

A simple LLM system usually follows a single linear path:

```mermaid
flowchart LR
    accTitle: Linear LLM Flow
    accDescr: A user request is sent to an LLM, which returns an answer directly without validation, state management, or feedback loops.

    user_request(["👤 User request"])
    llm["🧠 LLM"]
    answer(["✅ Answer"])

    user_request --> llm --> answer

    classDef input fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef intelligence fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
    classDef success fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d

    class user_request input
    class llm intelligence
    class answer success
```

This approach works for simple tasks. Once a system must use multiple tools, validate quality, revise failed results, wait for human approval, or continue after an interruption, a linear pipeline is no longer expressive enough.

Graph Engineering models a workflow as a set of steps with explicit responsibilities, allowing the system to:

- maintain state throughout execution;
- select branches based on runtime results;
- run independent nodes in parallel;
- evaluate and improve outputs;
- limit retries and control termination;
- checkpoint, pause, and resume;
- observe the complete execution path.

## Core Mental Model

Graph Engineering can be divided into three major areas:

```mermaid
flowchart TB
    accTitle: Three Pillars of Graph Engineering
    accDescr: Graph Engineering combines state for storing data, computation for performing work, and control for orchestrating execution.

    graph_engineering["Graph Engineering"]
    state["🗃️ State<br/>data · memory · reducers · checkpoints"]
    computation["⚙️ Computation<br/>LLM · agent · tool · API · human"]
    control["🚦 Control<br/>edges · routing · loops · termination"]

    state --> graph_engineering
    computation --> graph_engineering
    control --> graph_engineering

    classDef state_class fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e
    classDef computation_class fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
    classDef control_class fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef graph_class fill:#dcfce7,stroke:#16a34a,stroke-width:3px,color:#14532d

    class state state_class
    class computation computation_class
    class control control_class
    class graph_engineering graph_class
```

### State

State is the workflow's shared working memory at a given point in time. It may contain the query, category, evidence, intermediate results, feedback, quality score, retry count, final answer, and execution trace.

Instead of thinking:

> Node A produces output and passes it directly to Node B.

Think:

> Node A reads state and returns a state update; the runtime merges that update; Node B reads the new state.

Here is a minimal state definition for the notebook in this repository:

```python
class GraphState(TypedDict, total=False):
    query: str
    category: str
    evidence: list[str]
    analysis: str
    score: float
    feedback: str
    attempts: int
    final_answer: str
    route_log: Annotated[list[str], operator.add]
```

State should contain the data required for computation and routing, but it should not become a dumping ground for every temporary variable used by individual nodes.

### State Updates and Reducers

Not every field is updated in the same way. A reducer defines how the runtime combines an existing value with a new update.

| Data type | Example | Common strategy |
| --- | --- | --- |
| Current value | `category`, `score`, `feedback` | Overwrite with the new value |
| Accumulated history | `messages`, `route_log` | Append new items |
| Evidence collection | `evidence` | Merge and optionally deduplicate |
| Parallel results | `research_results` | Merge by key or source |

Reducers are especially important when nodes run in parallel or multiple nodes update the same field. Without clearly defined semantics, fan-in can create conflicts or cause data loss.

### Nodes

A node is a unit of computation. It does not have to be an agent, and it does not have to call an LLM.

A node can be:

- an LLM or agent;
- a tool or API call;
- a database query or retriever;
- a deterministic function;
- an evaluator or schema validator;
- a human approval step;
- a subgraph.

> **A node is not synonymous with an agent. Use an LLM only where intelligence is genuinely required.**

### Edges and Execution Patterns

An edge determines which node runs next. The three foundational patterns are normal edges, conditional edges, and fan-out/fan-in.

```mermaid
flowchart TB
    accTitle: Three Foundational Edge Patterns
    accDescr: The diagram compares a fixed flow, a conditional flow, and a parallel flow that splits into independent branches before merging.

    subgraph normal_edge["Normal edge"]
        direction LR
        normal_a["A"] --> normal_b["B"]
    end

    subgraph conditional_edge["Conditional edge"]
        direction LR
        evaluate["Evaluate"] --> decision{"Condition?"}
        decision -->|"True"| path_b["B"]
        decision -->|"False"| path_c["C"]
    end

    subgraph parallel_edge["Fan-out / Fan-in"]
        direction LR
        input["Input"] --> source_a["Source A"]
        input --> source_b["Source B"]
        input --> source_c["Source C"]
        source_a --> aggregate["Aggregate"]
        source_b --> aggregate
        source_c --> aggregate
    end

    classDef work fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
    classDef gate fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef merge fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d

    class normal_a,normal_b,evaluate,path_b,path_c,input,source_a,source_b,source_c work
    class decision gate
    class aggregate merge
```

### Nodes and Routers

Nodes and routers have different responsibilities:

| Component | Input | Responsibility | Output |
| --- | --- | --- | --- |
| Node | State | Perform computation | State update |
| Router | State | Select the next edge | Route or next node |

For example, an evaluator may produce `score = 0.72`; the router reads that score and decides to return to the improvement node because the score is below the threshold.

> **Nodes compute; routers control.**

## The Graph as a Control Plane

A graph is not merely a collection of connected LLMs. It is the control plane that manages state, execution order, and system policy.

| Type of work | Appropriate component |
| --- | --- |
| Semantic understanding, reasoning, critique, text generation | LLM |
| External data retrieval | Tool, API, database, retriever |
| Exact calculations and schema validation | Deterministic code |
| Routing, retry limits, timeouts, termination | Graph and Python policy |
| Approval of high-risk actions | Human |
| Execution persistence and recovery | Checkpointer/runtime |

A development workflow with a graph control plane can be organized as follows:

```mermaid
flowchart LR
    accTitle: Graph-Orchestrated Development Workflow
    accDescr: The graph orchestrates a Planner, Developer, Reviewer, and Tester through quality gates. Nodes read and update shared state throughout the workflow.

    user(["👤 User"])

    subgraph control_plane["Graph control plane"]
        direction LR
        planner["🗺️ Planner"]
        developer["💻 Developer"]
        reviewer["🔍 Reviewer"]
        review_gate{"Review passed?"}
        tester["🧪 Tester"]
        test_gate{"Tests passed?"}
        final(["✅ Final"])

        planner --> developer --> reviewer --> review_gate
        review_gate -->|"Revise"| developer
        review_gate -->|"Approved"| tester --> test_gate
        test_gate -->|"Failed"| developer
        test_gate -->|"Passed"| final
    end

    shared_state[("🗃️ Shared state")]

    user --> planner
    planner -.->|"plan"| shared_state
    developer -.->|"artifacts"| shared_state
    reviewer -.->|"feedback"| shared_state
    tester -.->|"test results"| shared_state

    classDef input fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef agent fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
    classDef gate fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef data fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e
    classDef success fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d

    class user input
    class planner,developer,reviewer,tester agent
    class review_gate,test_gate gate
    class shared_state data
    class final success
```

The mental model to remember is:

> **LLMs provide intelligence. Graphs provide control. Tools provide capabilities. State connects everything.**

## Loops, Feedback, and Termination

### Loop Engineering and Graph Engineering

Loop Engineering focuses on an iteration that improves a result. Graph Engineering covers the entire topology: multiple nodes, branches, shared state, parallelism, quality gates, human approval, persistence, and termination.

A loop is therefore one pattern within Graph Engineering.

```mermaid
flowchart TD
    accTitle: Code Repair Loop
    accDescr: An agent writes code, runs tests, and checks the result. When tests fail, it reads the error, fixes the code, and runs the tests again until they pass.

    write_code["💻 Write code"]
    run_tests["🧪 Run tests"]
    tests_passed{"Tests passed?"}
    read_error["📋 Read error"]
    fix_code["🛠️ Fix code"]
    success(["✅ Success"])

    write_code --> run_tests --> tests_passed
    tests_passed -->|"No"| read_error --> fix_code --> run_tests
    tests_passed -->|"Yes"| success

    classDef action fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
    classDef gate fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef repair fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef success fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d

    class write_code,run_tests action
    class tests_passed gate
    class read_error,fix_code repair
    class success success
```

### Retry vs. Improvement

`Generate → Fail → Generate again` is only a retry. If the state, information, or strategy does not change, the next attempt may repeat exactly the same failure.

A useful feedback loop follows this pattern:

`Generate → Evaluate → Feedback → Improve → Generate again`

Improvement must introduce a meaningful change, such as:

- adding evidence;
- updating the plan or prompt;
- choosing a different tool or model;
- applying evaluator feedback;
- delegating the task to a more specialized agent.

> **Every iteration should improve the state, information, or strategy.**

### Quality Gates

A quality gate is a control point that determines whether a result is good enough to proceed. A gate may check evidence, test results, risk, confidence, safety, or human approval.

Evaluators and gates should also be kept distinct:

- An evaluator produces assessment data such as a `score`, `feedback`, or validation result.
- A gate or router applies a policy such as `score >= 0.8` to select `finish` or `retry`.

### Termination Policies

Every graph with a loop must answer:

1. When is the workflow considered successful?
2. What is the maximum number of retries?
3. When should the workflow fall back or abort?
4. When should it escalate to a human?
5. When should it accept an imperfect but sufficient result?

| Termination type | Purpose | Example |
| --- | --- | --- |
| Quality termination | Stop when requirements are met | `score >= threshold` |
| Safety termination | Prevent infinite loops or budget overruns | `attempts >= max_retries` |
| Operational termination | Stop because of runtime conditions | deadline, cancellation, unrecoverable error |
| Human termination | Wait for or terminate based on a reviewer's decision | approve, reject, request changes |

> **Feedback loop + termination policy = controlled iteration.**

## Graph Engineering and Multi-Agent Systems

The two concepts address different dimensions:

| Concept | Primary question |
| --- | --- |
| Multi-Agent | How many agents are there, what roles do they have, and how do they communicate? |
| Graph Engineering | What path does the workflow follow, how is state passed, and when does it branch, loop, or terminate? |

Graph Engineering does not require multiple agents. A single coding agent moving through code, test, fix, and termination nodes still forms a graph.

Conversely, multiple agents exchanging messages freely do not necessarily form a clearly orchestrated graph. Multi-Agent design emphasizes specialization and collaboration; Graph Engineering emphasizes orchestration and control.

```mermaid
flowchart TD
    accTitle: Graph-Orchestrated Multi-Agent System
    accDescr: A Manager delegates research while quality gates validate evidence, risk, and drafts. Each failed branch returns feedback to the responsible agent, while successful branches progress toward END.

    start(["▶️ START"])
    manager["🧭 Manager"]
    researcher["🔎 Researcher"]
    evidence_gate{"Evidence sufficient?"}
    analyst["📊 Analyst"]
    risk_gate{"Risk acceptable?"}
    writer["✍️ Writer"]
    reviewer["🔍 Reviewer"]
    review_gate{"Draft accepted?"}
    end_node(["✅ END"])

    start --> manager --> researcher --> evidence_gate
    evidence_gate -->|"Insufficient"| researcher
    evidence_gate -->|"Sufficient"| analyst --> risk_gate
    risk_gate -->|"Fail · revise analysis"| analyst
    risk_gate -->|"Pass"| writer --> reviewer --> review_gate
    review_gate -->|"Reject · feedback"| writer
    review_gate -->|"Accept"| end_node

    classDef terminal fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef coordinator fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef agent fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
    classDef gate fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f

    class start,end_node terminal
    class manager coordinator
    class researcher,analyst,writer,reviewer agent
    class evidence_gate,risk_gate,review_gate gate
```

> **Multi-Agent systems provide specialization; Graph Engineering provides orchestration.**

## Essential Execution Patterns

### Parallelism and Fan-Out/Fan-In

Independent nodes can run in parallel to reduce latency and increase coverage. After fan-out, the graph needs a fan-in point to synchronize and aggregate their results.

```mermaid
flowchart LR
    accTitle: Parallel Research Workflow
    accDescr: A query is distributed to three independent research branches, whose results are merged before moving to analysis.

    query(["👤 Query"])
    weather["🌤️ Weather research"]
    trade["📦 Trade research"]
    politics["🏛️ Politics research"]
    aggregate["🔗 Aggregate evidence"]
    analysis["🧠 Analysis"]

    query --> weather
    query --> trade
    query --> politics
    weather --> aggregate
    trade --> aggregate
    politics --> aggregate
    aggregate --> analysis

    classDef input fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef work fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
    classDef merge fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef output fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d

    class query input
    class weather,trade,politics work
    class aggregate merge
    class analysis output
```

Parallelism introduces decisions about reducers, conflict resolution, synchronization, and fan-in policy. Nodes that depend on one another's unfinished outputs should not run in parallel.

### Persistence and Durable Execution

State describes the current data; a checkpoint is a snapshot of state; a thread is a sequence of checkpoints belonging to the same execution or conversation.

```mermaid
flowchart LR
    accTitle: Durable Execution with Checkpoints
    accDescr: The workflow stores checkpoints after important steps so it can pause, wait for a human, recover from failure, and continue without restarting from the beginning.

    node_a["⚙️ Node A"]
    checkpoint_a[("💾 Checkpoint")]
    node_b["⚙️ Node B"]
    risky_action{"High-risk action?"}
    human_review["👤 Human review"]
    resume["▶️ Resume"]
    node_c["⚙️ Node C"]
    done(["✅ END"])

    node_a --> checkpoint_a --> node_b --> risky_action
    risky_action -->|"No"| node_c
    risky_action -->|"Yes · pause"| human_review
    human_review -->|"Approve"| resume --> node_c
    human_review -->|"Request changes"| node_a
    node_c --> done
    node_b -.->|"Crash · restore"| checkpoint_a

    classDef work fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
    classDef storage fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e
    classDef gate fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef human fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef success fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d

    class node_a,node_b,node_c,resume work
    class checkpoint_a storage
    class risky_action gate
    class human_review human
    class done success
```

Persistence supports long-running workflows, crash recovery, human-in-the-loop interactions, replay, auditing, and debugging. Actions with side effects also require idempotency so that resuming does not send an email, write to a database, or process a payment twice.

### Human-in-the-Loop

Humans are not outside the graph; they are control points within it. A graph can pause before a high-risk action, save a checkpoint, wait for approval, rejection, or edits, and then resume within the correct thread.

Typical use cases include sending important emails, deleting data, processing transactions, changing production systems, or publishing content.

### Subgraphs

As a graph grows, it should be divided into subgraphs by responsibility, such as Research, Analysis, and Review. The parent graph treats each subgraph as a high-level node.

Subgraphs help reuse logic, isolate state, test components independently, and reduce the complexity of the parent graph. Their input/output contracts and the state fields shared between parent and child graphs must be defined explicitly.

## Reliability and Observability

### Semantic Failures and Runtime Failures

A production graph must distinguish poor results from technical failures because the two failure classes require different policies.

| Failure type | Symptoms | Appropriate handling |
| --- | --- | --- |
| Semantic failure | Missing evidence, weak analysis, incorrect intent, low confidence | Evaluate, provide feedback, retrieve more, revise |
| Runtime failure | Timeout, rate limit, API error, invalid response, unavailable database | Retry with backoff, fallback, circuit breaker, graceful failure |

```mermaid
flowchart LR
    accTitle: Failure Handling Policy
    accDescr: Failures are classified as semantic or runtime failures so the graph can apply the appropriate content-improvement or technical-recovery policy.

    failure{"Failure type?"}
    semantic["Semantic failure"]
    runtime["Runtime failure"]
    improve["Evaluate · feedback<br/>retrieve · revise"]
    recover["Retry · backoff<br/>fallback · abort"]
    workflow["Return to workflow"]

    failure -->|"Output below standard"| semantic --> improve --> workflow
    failure -->|"Execution error"| runtime --> recover --> workflow

    classDef gate fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef semantic_class fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
    classDef runtime_class fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef success fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d

    class failure gate
    class semantic,improve semantic_class
    class runtime,recover runtime_class
    class workflow success
```

Runtime retries should be bounded, use backoff, and apply only to recoverable errors. Semantic retries must change the context or strategy.

### Deterministic Control and Probabilistic Reasoning

LLMs are probabilistic, while many graph policies need to be deterministic.

| Use an LLM when | Use deterministic logic when |
| --- | --- |
| Semantic or intent understanding is required | A clear threshold exists |
| Reasoning, planning, or critique is required | Schema validation is required |
| Summarization or text generation is required | Exact calculations are required |
| The rules cannot be fully enumerated in code | Permissions, timeouts, or retry limits are involved |

A safe pattern is to let the LLM produce decision data, then have a Python router validate it and apply policy. An LLM should not have unilateral control over unlimited retries, permissions, or high-risk actions.

### Observability

The final answer tells you what the system produced. The execution trace tells you what the system did to produce it.

A production graph should expose:

- the nodes and paths that ran;
- each node's input/output or state update;
- router decisions and their reasons;
- retry counts, failure types, and termination reasons;
- latency, token usage, and cost;
- the models, tools, and external dependencies used;
- checkpoints, threads, and correlation IDs.

Logs should not contain API keys, credentials, personal data, or complete sensitive prompts. Observability must be paired with redaction and access control.

## Reference Production Architecture

A complete graph-based system commonly includes the following layers:

```mermaid
flowchart TB
    accTitle: Production Agentic Graph Architecture
    accDescr: A request passes through planning, retrieval, analysis, evaluation, and routing, while persistence, observability, and policy layers support the full execution lifecycle.

    input(["👤 Input + context"])
    planning["🗺️ Classification / planning"]

    subgraph execution["Execution graph"]
        direction LR
        retrieval["🔎 Tool / retrieval"]
        analysis["🧠 Analysis"]
        evaluation["📏 Evaluation"]
        routing{"Routing policy"}

        retrieval --> analysis --> evaluation --> routing
        routing -->|"Retrieve more"| retrieval
        routing -->|"Revise"| analysis
    end

    human["👤 Human approval"]
    output(["✅ Final output"])

    persistence[("💾 Persistence<br/>state · checkpoint · thread")]
    observability["📈 Observability<br/>trace · metrics · cost"]
    policy["🛡️ Reliability policy<br/>retry · timeout · fallback"]

    input --> planning --> retrieval
    routing -->|"Approval required"| human
    human -->|"Approved"| output
    human -->|"Changes requested"| analysis
    routing -->|"Finish"| output

    planning -.-> persistence
    retrieval -.-> persistence
    analysis -.-> persistence
    evaluation -.-> persistence
    execution -.-> observability
    policy -.-> execution

    classDef input_class fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef work fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
    classDef gate fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef support fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e
    classDef human_class fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef success fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d

    class input input_class
    class planning,retrieval,analysis,evaluation work
    class routing gate
    class persistence,observability,policy support
    class human human_class
    class output success
```

These layers do not necessarily need to be separate nodes. Persistence and observability are usually runtime capabilities that span the entire workflow; routing and termination can live in code-based policies rather than LLM nodes.

## Conclusion

Graph Engineering is not simply the practice of connecting multiple agents or LLMs. It is the design of a stateful control system for AI: the system knows where it is, which step should run next, how to evaluate results, when to revise, how to recover from failure, and when to terminate.

At the foundational level:

> **Graph Engineering = State + Computation + Control.**

At the production level:

> **Graph Engineering = State management + Node design + Control flow + Evaluation + Feedback + Persistence + Reliability + Observability.**
