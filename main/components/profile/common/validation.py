"""
common/validation.py

Cross-cutting validation helpers used by the Capacity Engine and the
Profile Assembler to guard against malformed data.

All helpers raise ValueError (or a subclass) on failure so that callers
can catch them uniformly and surface structured error messages.
"""
from __future__ import annotations

import math
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Primitive guards
# ---------------------------------------------------------------------------


def assert_finite(value: float, field_name: str) -> float:
    """Raise ValueError if value is NaN or infinite."""
    if not math.isfinite(value):
        raise ValueError(
            f"Field '{field_name}' must be a finite number; got {value!r}"
        )
    return value


def assert_non_negative(value: float, field_name: str) -> float:
    """Raise ValueError if value is negative."""
    assert_finite(value, field_name)
    if value < 0:
        raise ValueError(
            f"Field '{field_name}' must be ≥ 0; got {value}"
        )
    return value


def assert_positive(value: float, field_name: str) -> float:
    """Raise ValueError if value is not strictly positive."""
    assert_finite(value, field_name)
    if value <= 0:
        raise ValueError(
            f"Field '{field_name}' must be > 0; got {value}"
        )
    return value


def assert_ratio(value: float, field_name: str) -> float:
    """Raise ValueError if value is not in [0, 1]."""
    assert_finite(value, field_name)
    if not (0.0 <= value <= 1.0):
        raise ValueError(
            f"Field '{field_name}' must be in [0, 1]; got {value}"
        )
    return value


def assert_score(value: Optional[float], field_name: str) -> Optional[float]:
    """Raise ValueError if a non-None score is outside [0, 100]."""
    if value is None:
        return None
    assert_finite(value, field_name)
    if not (0.0 <= value <= 100.0):
        raise ValueError(
            f"Field '{field_name}' must be in [0, 100]; got {value}"
        )
    return value


# ---------------------------------------------------------------------------
# Component-result contract validation
# ---------------------------------------------------------------------------


class ComponentContractError(ValueError):
    """Raised when a component result does not satisfy its public contract."""

    def __init__(self, component: str, message: str) -> None:
        self.component = component
        super().__init__(f"[{component}] Contract violation: {message}")


def validate_component_result(result: Any, component_name: str) -> None:
    """
    Validate that a component result satisfies the common output contract.

    Checks:
      - score: None or 0–100
      - confidence: 0–1 (and is a float, not e.g. 80 for 0.80)
      - features: dict
      - reasons: list
      - warnings: list

    Raises ComponentContractError on the first violation found.
    """
    # confidence
    try:
        conf = result.confidence
    except AttributeError:
        raise ComponentContractError(component_name, "missing 'confidence' field")

    if not isinstance(conf, (int, float)):
        raise ComponentContractError(
            component_name,
            f"confidence must be a numeric value in [0, 1]; got {conf!r}",
        )
    if not math.isfinite(conf):
        raise ComponentContractError(
            component_name,
            f"confidence must be finite; got {conf}",
        )
    if not (0.0 <= conf <= 1.0):
        raise ComponentContractError(
            component_name,
            f"confidence must be in [0, 1]; got {conf}. "
            "Do NOT supply confidence as a percentage (e.g. 80 instead of 0.80).",
        )

    # score (optional — can be None)
    try:
        score = result.score
    except AttributeError:
        raise ComponentContractError(component_name, "missing 'score' field")

    if score is not None:
        if not isinstance(score, (int, float)):
            raise ComponentContractError(
                component_name,
                f"score must be numeric or None; got {score!r}",
            )
        if not math.isfinite(score):
            raise ComponentContractError(
                component_name,
                f"score must be finite; got {score}",
            )
        if not (0.0 <= score <= 100.0):
            raise ComponentContractError(
                component_name,
                f"score must be in [0, 100]; got {score}",
            )

    # features
    if not hasattr(result, "features") or not isinstance(result.features, dict):
        raise ComponentContractError(
            component_name, "features must be a dict"
        )

    # reasons
    if not hasattr(result, "reasons") or not isinstance(result.reasons, list):
        raise ComponentContractError(
            component_name, "reasons must be a list"
        )

    # warnings
    if not hasattr(result, "warnings") or not isinstance(result.warnings, list):
        raise ComponentContractError(
            component_name, "warnings must be a list"
        )
