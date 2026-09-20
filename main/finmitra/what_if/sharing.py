"""Privacy-safe serialization for explicitly shared What If summaries."""

from __future__ import annotations

from .schemas import ShareableGoal, ShareableWhatIfSummary, WhatIfResult


def to_shareable_summary(
    result: WhatIfResult, *, include_title: bool = False
) -> ShareableWhatIfSummary:
    """Return an allowlisted summary with no income, expenses, or capacity data."""

    monthly_gap = (
        result.gap.monthly_cashflow_gap
        if result.goal.type == "LOAN_READINESS"
        else result.gap.monthly_savings_gap
    )
    return ShareableWhatIfSummary(
        outcome=result.outcome,
        goal=ShareableGoal(
            type=result.goal.type,
            title=result.goal.title if include_title else None,
            target_amount=result.goal.target_amount,
            deadline_months=result.goal.deadline_months,
            annual_interest_rate=result.goal.annual_interest_rate,
            tenure_months=result.goal.tenure_months,
        ),
        required_emi=result.required_state.required_emi,
        required_monthly_saving=result.required_state.required_monthly_saving,
        monthly_gap=monthly_gap,
        new_credit_blocked=result.safety.new_credit_blocked,
    )
