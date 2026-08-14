from langgraph.types import Command

from graph_engineering.human_loop import build_human_loop_graph, human_thread_config


def _pause_high_risk(thread_id: str):
    graph, _ = build_human_loop_graph()
    config = human_thread_config(thread_id)
    paused = graph.invoke(
        {"request": "publish pricing", "risk_level": "high", "trace": []},
        config,
    )
    return graph, config, paused


def test_high_risk_execution_pauses_before_protected_action():
    graph, config, paused = _pause_high_risk("pause-test")

    assert "__interrupt__" in paused
    assert "execute" not in paused["trace"]
    assert graph.get_state(config).next == ("human_review",)


def test_human_approval_resumes_and_executes():
    graph, config, _ = _pause_high_risk("approve-test")

    result = graph.invoke(Command(resume={"decision": "approve"}), config)

    assert result["action_executed"] is True
    assert result["termination_reason"] == "approved_and_executed"


def test_human_rejection_does_not_execute_protected_action():
    graph, config, _ = _pause_high_risk("reject-test")

    result = graph.invoke(Command(resume={"decision": "reject"}), config)

    assert result["action_executed"] is False
    assert result["termination_reason"] == "human_rejected"
    assert "execute" not in result["trace"]


def test_human_revision_loop_stops_at_configured_bound():
    graph, config, _ = _pause_high_risk("revision-budget-test")

    repaused = graph.invoke(
        Command(
            resume={"decision": "revise", "requested_changes": "remove identifiers"}
        ),
        config,
    )
    assert repaused["revisions"] == 1
    assert graph.get_state(config).next == ("human_review",)

    stopped = graph.invoke(Command(resume={"decision": "revise"}), config)
    assert stopped["action_executed"] is False
    assert stopped["termination_reason"] == "revision_budget_exhausted"
