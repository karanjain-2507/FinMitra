"""Deterministic backward-planning tools for FinMitra financial goals."""

from .adapters import BaselineDataError, baseline_from_assessment
from .engine import WhatIfEngine
from .schemas import (
    Goal,
    LoanReadinessGoal,
    SavingsTargetGoal,
    ShareableWhatIfSummary,
    WhatIfResult,
)
from .sharing import to_shareable_summary

__all__ = [
    "BaselineDataError",
    "Goal",
    "LoanReadinessGoal",
    "SavingsTargetGoal",
    "ShareableWhatIfSummary",
    "WhatIfEngine",
    "WhatIfResult",
    "baseline_from_assessment",
    "to_shareable_summary",
]
