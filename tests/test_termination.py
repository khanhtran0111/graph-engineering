from graph_engineering.feedback import MAX_ATTEMPTS, build_feedback_graph


def test_retry_budget_is_respected():
    graph = build_feedback_graph(score_fn=lambda _state: 0.1)
    result = graph.invoke({"topic": "bounded loops", "attempts": 0, "trace": []})

    assert result["attempts"] == MAX_ATTEMPTS
    assert result["termination_reason"] == "attempt_budget_exhausted"


def test_graph_terminates_when_quality_is_reached():
    graph = build_feedback_graph(score_fn=lambda _state: 0.95)
    result = graph.invoke({"topic": "quality gates", "attempts": 0, "trace": []})

    assert result["attempts"] == 1
    assert result["termination_reason"] == "quality_reached"
