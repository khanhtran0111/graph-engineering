from graph_engineering.parallelism import SOURCES, build_parallel_graph


def test_parallel_branches_merge_without_losing_results():
    result = build_parallel_graph().invoke({"question": "Does heat affect sales?"})

    assert sorted(result["source_results"]) == sorted(SOURCES.items())
    assert len(result["evidence"]) == len(SOURCES)
    assert result["termination_reason"] == "all_sources_succeeded"


def test_parallel_partial_failure_preserves_successful_results():
    result = build_parallel_graph({"market"}).invoke({"question": "question"})

    assert result["source_errors"] == ["market"]
    assert {name for name, _ in result["source_results"]} == {"climate", "grid"}
    assert result["termination_reason"] == "partial_success"
