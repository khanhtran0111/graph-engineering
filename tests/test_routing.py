import pytest

from graph_engineering.control import classify_keywords, route_category


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Will heavy rain affect demand?", "weather"),
        ("How could a tariff change imports?", "trade"),
        ("What policy did the government announce?", "politics"),
    ],
)
def test_router_selects_expected_branch(question: str, expected: str):
    category = classify_keywords(question)
    assert route_category({"category": category}) == expected


def test_router_rejects_unknown_branch():
    with pytest.raises(ValueError, match="Unsupported category"):
        route_category({"category": "finance"})
