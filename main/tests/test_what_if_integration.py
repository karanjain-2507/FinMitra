from finmitra.demo import build_demo
from finmitra.runner import assess
from finmitra.schemas import IntegratedBorrowerInput
from finmitra.what_if import WhatIfEngine, baseline_from_assessment
from finmitra.what_if.schemas import LoanReadinessGoal


def test_strong_demo_assessment_drives_what_if_and_matches_capacity_emi():
    raw = build_demo("strong")
    raw["capacity_context"].update(
        requested_loan_amount=100000,
        annual_interest_rate=0.14,
        tenure_months=24,
    )
    assessment = assess(IntegratedBorrowerInput.model_validate(raw))
    goal = LoanReadinessGoal(
        type="LOAN_READINESS",
        title="Car",
        target_amount=100000,
        deadline_months=8,
        annual_interest_rate=0.14,
        tenure_months=24,
    )
    plan = WhatIfEngine.plan(baseline_from_assessment(assessment), goal)
    capacity_emi = assessment["profile"]["capacity"]["requested_loan"]["calculated_emi"]
    assert float(plan.required_state.required_emi) == capacity_emi
    assert plan.current_state.monthly_surplus == assessment["profile"]["capacity"]["features"]["monthly_surplus"]
