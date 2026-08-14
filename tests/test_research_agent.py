import pytest

from examples.research_agent.versions import build_version


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_research_agent_version_terminates(version: int):
    result = build_version(version).invoke(
        {"question": "Will extreme heat change AC sales?", "trace": []}
    )

    assert result["termination_reason"]
    assert result["final_answer"]


def test_research_agent_routes_expected_domain():
    result = build_version(2).invoke(
        {"question": "Will extreme heat change AC sales?", "trace": []}
    )

    assert result["category"] == "weather"
    assert "research:weather" in result["trace"]
