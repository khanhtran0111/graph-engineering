from graph_engineering.subgraphs import build_subgraph_system


def test_parent_receives_only_documented_child_outputs():
    result = build_subgraph_system().invoke(
        {"question": "Will heat change demand?", "trace": []}
    )

    assert result["termination_reason"] == "completed"
    assert result["trace"] == [
        "research_subgraph",
        "analysis_subgraph",
        "review_subgraph",
    ]
    assert "raw_results" not in result
    assert "validation_notes" not in result
    assert "private_scratchpad" not in result
    assert "reviewer_note" not in result
