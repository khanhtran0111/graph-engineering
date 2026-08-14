"""Framework-independent routing helpers and policy decisions."""

from typing import Literal, Mapping

Category = Literal["weather", "trade", "politics"]
QualityRoute = Literal["complete", "improve", "fallback"]

CATEGORIES: tuple[Category, ...] = ("weather", "trade", "politics")


def classify_keywords(text: str) -> Category:
    """Provide a deterministic classifier for lessons and tests."""

    normalized = text.casefold()
    if any(word in normalized for word in ("weather", "rain", "heat", "climate")):
        return "weather"
    if any(word in normalized for word in ("trade", "tariff", "import", "export")):
        return "trade"
    return "politics"


def route_category(state: Mapping[str, object]) -> Category:
    """Validate a structured category before selecting an edge."""

    category = state.get("category")
    if category not in CATEGORIES:
        raise ValueError(f"Unsupported category: {category!r}")
    return category  # type: ignore[return-value]


def route_quality(
    state: Mapping[str, object],
    *,
    threshold: float,
    max_attempts: int,
) -> QualityRoute:
    """Apply deterministic success and attempt-budget policy."""

    score = float(state.get("score", 0.0))
    attempts = int(state.get("attempts", 0))
    if score >= threshold:
        return "complete"
    if attempts >= max_attempts:
        return "fallback"
    return "improve"
