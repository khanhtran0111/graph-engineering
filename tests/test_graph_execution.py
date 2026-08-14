import pytest

from graph_engineering.fundamentals import build_number_graph


@pytest.mark.parametrize(
    ("value", "category", "expected", "last_node"),
    [(6, "even", 12, "multiply"), (5, "odd", 8, "add")],
)
def test_graph_execution_follows_selected_branch(
    value: int,
    category: str,
    expected: int,
    last_node: str,
):
    result = build_number_graph().invoke({"value": value, "trace": []})

    assert result["category"] == category
    assert result["result"] == expected
    assert result["trace"] == [f"classify:{category}", last_node]
