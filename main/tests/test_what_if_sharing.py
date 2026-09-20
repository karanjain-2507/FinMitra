from finmitra.demo import build_demo
from finmitra.runner import assess
from finmitra.schemas import IntegratedBorrowerInput
from finmitra.what_if import WhatIfEngine, baseline_from_assessment, to_shareable_summary
from finmitra.what_if.schemas import LoanReadinessGoal


def test_share_summary_is_allowlisted_and_omits_financial_baseline():
    assessment = assess(IntegratedBorrowerInput.model_validate(build_demo("strong")))
    result = WhatIfEngine.plan(
        baseline_from_assessment(assessment),
        LoanReadinessGoal(
            type="LOAN_READINESS",
            title="Private car label",
            target_amount=100000,
            deadline_months=8,
            annual_interest_rate=0.14,
            tenure_months=24,
        ),
    )
    shared = to_shareable_summary(result).model_dump(mode="json")

    assert shared["goal"]["title"] is None
    assert "current_state" not in shared
    assert "monthly_inflow" not in str(shared)
    assert "available_balance_buffer" not in str(shared)
    assert set(shared) == {
        "schema_version",
        "outcome",
        "goal",
        "required_emi",
        "required_monthly_saving",
        "monthly_gap",
        "new_credit_blocked",
    }
