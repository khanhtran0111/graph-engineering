from graph_engineering.multi_agent import build_multi_agent_graph


def test_multi_agent_handoff_respects_explicit_routing_policy():
    result = build_multi_agent_graph().invoke(
        {"task": "compare forecasts", "requested_role": "analysis"}
    )

    assert result["selected_agent"] == "analysis_agent"
    assert result["handoffs"][:2] == [
        ("manager", "analysis_agent"),
        ("analysis_agent", "reviewer"),
    ]
    assert result["termination_reason"] == "quality_reached"


def test_multi_agent_unknown_role_uses_allowed_fallback():
    result = build_multi_agent_graph().invoke(
        {"task": "do work", "requested_role": "unbounded_supervisor"}
    )

    assert result["fallback_used"] is True
    assert result["selected_agent"] == "research_agent"
    assert result["handoffs"][0] == ("manager", "research_agent")
