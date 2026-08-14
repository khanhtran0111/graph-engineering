from graph_engineering.fundamentals import classify_number


def test_state_updates_are_explicit():
    state = {"value": 4, "trace": []}
    original = {"value": 4, "trace": []}

    update = classify_number(state)

    assert state == original
    assert update == {"category": "even", "trace": ["classify:even"]}
    assert "value" not in update
