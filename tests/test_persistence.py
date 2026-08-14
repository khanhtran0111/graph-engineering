from graph_engineering.persistence import build_checkpoint_graph, thread_config


def test_checkpoint_resume_continues_same_run_without_replaying_earlier_nodes():
    graph, ledger, _ = build_checkpoint_graph()
    config = thread_config("checkpoint-test")

    paused = graph.invoke(
        {
            "request": "publish report",
            "idempotency_key": "publish-001",
            "visits": [],
        },
        config,
    )
    assert paused["visits"] == ["prepare", "research", "review"]
    assert graph.get_state(config).next == ("protected_action",)

    resumed = graph.invoke(None, config)
    assert resumed["visits"] == [
        "prepare",
        "research",
        "review",
        "protected_action",
        "finish",
    ]
    assert resumed["termination_reason"] == "completed"
    assert ledger.execution_count == 1


def test_idempotency_key_executes_simulated_action_at_most_once():
    graph, ledger, _ = build_checkpoint_graph()
    first = thread_config("first-run")
    second = thread_config("replayed-request")
    input_state = {
        "request": "charge customer",
        "idempotency_key": "charge-001",
        "visits": [],
    }

    graph.invoke(input_state, first)
    graph.invoke(None, first)
    graph.invoke(input_state, second)
    replay = graph.invoke(None, second)

    assert ledger.execution_count == 1
    assert replay["action_status"] == "already_executed"
