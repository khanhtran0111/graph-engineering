from graph_engineering.parallelism import merge_source_results


def test_reducer_preserves_all_expected_updates():
    merged = merge_source_results(
        [("a", "first")],
        [("b", "second"), ("c", "third")],
    )

    assert merged == [("a", "first"), ("b", "second"), ("c", "third")]
