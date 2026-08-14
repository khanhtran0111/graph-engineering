from graph_engineering.dynamic import ALLOWED_TOOLS, MAX_DEPTH, MAX_WORKERS, build_dynamic_graph


def test_dynamic_fan_out_never_exceeds_configured_bound():
    items = [f"item-{index}" for index in range(MAX_WORKERS + 4)]
    result = build_dynamic_graph().invoke(
        {"discovered_items": items, "depth": 0, "allowed_tools": ALLOWED_TOOLS}
    )

    assert result["fan_out_count"] == MAX_WORKERS
    assert len(result["worker_results"]) == MAX_WORKERS
    assert {item for item, _, _ in result["worker_results"]} == set(items[:MAX_WORKERS])


def test_dynamic_depth_limit_prevents_new_workers():
    result = build_dynamic_graph().invoke(
        {"discovered_items": ["a", "b"], "depth": MAX_DEPTH}
    )

    assert result["fan_out_count"] == 0
    assert result.get("worker_results", []) == []
    assert result["termination_reason"] == "depth_limit_reached"


def test_dynamic_worker_never_uses_a_tool_outside_the_allow_list():
    result = build_dynamic_graph().invoke(
        {"discovered_items": ["a"], "depth": 0, "allowed_tools": ("shell",)}
    )

    assert result["worker_results"][0][1] in ALLOWED_TOOLS
    assert result["worker_results"][0][1] != "shell"
