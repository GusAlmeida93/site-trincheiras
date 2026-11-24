"""Scoring rules for activities. Pure: no database access."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


def _as_int(value: Any, fallback: int) -> int:
    # Activity config is free-form JSON, so every value is validated on read.
    # bool is an int subclass and must not count as a number here.
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return fallback


@dataclass(frozen=True)
class ScoringRules:
    points_correct: int = 10
    points_wrong: int = -5
    # Wrong answers to one question stop costing points after this many.
    max_penalized_errors: int = 2

    @classmethod
    def from_config(cls, config: Mapping[str, Any] | None) -> "ScoringRules":
        raw = config or {}
        defaults = cls()
        return cls(
            points_correct=_as_int(raw.get("points_correct"), defaults.points_correct),
            points_wrong=_as_int(raw.get("points_wrong"), defaults.points_wrong),
            max_penalized_errors=_as_int(
                raw.get("max_penalized_errors"), defaults.max_penalized_errors
            ),
        )

    def score_delta(self, is_correct: bool, prior_errors: int) -> int:
        """Points for one answer, given the wrong answers that came before it."""
        if is_correct:
            return self.points_correct
        if prior_errors < self.max_penalized_errors:
            return self.points_wrong
        return 0
