from graph_engineering.reliability import build_recovery_graph


def test_transient_failure_respects_runtime_retry_budget():
    result = build_recovery_graph().invoke(
        {
            "runtime_outcomes": ["transient", "transient", "transient"],
            "quality_scores": [1.0],
            "max_runtime_retries": 2,
            "max_semantic_attempts": 2,
        }
    )

    assert result["runtime_retries"] == 2
    assert result["execution_calls"] == 3
    assert result["termination_reason"] == "runtime_retry_budget_exhausted"


def test_transient_failure_can_recover_within_runtime_retry_budget():
    result = build_recovery_graph().invoke(
        {
            "runtime_outcomes": ["transient", "success"],
            "quality_scores": [0.9],
            "max_runtime_retries": 2,
            "max_semantic_attempts": 1,
        }
    )

    assert result["runtime_retries"] == 1
    assert result["execution_calls"] == 2
    assert result["termination_reason"] == "quality_reached"


def test_permanent_failure_is_not_retried():
    result = build_recovery_graph().invoke(
        {
            "runtime_outcomes": ["permanent", "success"],
            "quality_scores": [1.0],
            "max_runtime_retries": 3,
            "max_semantic_attempts": 2,
        }
    )

    assert result["execution_calls"] == 1
    assert result["runtime_retries"] == 0
    assert result["termination_reason"] == "permanent_failure"


def test_semantic_failure_changes_strategy_before_retry():
    result = build_recovery_graph().invoke(
        {
            "runtime_outcomes": ["success", "success"],
            "quality_scores": [0.4, 0.9],
            "max_runtime_retries": 1,
            "max_semantic_attempts": 2,
        }
    )

    assert result["semantic_attempts"] == 2
    assert result["strategy_history"] == ["baseline", "evidence_expansion_1"]
    assert result["artifact"] == "answer using evidence_expansion_1"
    assert result["termination_reason"] == "quality_reached"
