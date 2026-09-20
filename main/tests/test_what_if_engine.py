from datetime import date
from decimal import Decimal

from finmitra.what_if.engine import WhatIfEngine
from finmitra.what_if.schemas import (
    FinancialBaseline,
    LoanReadinessGoal,
    SavingsTargetGoal,
    StressTestSummary,
)


def baseline(**overrides):
    data = {
        "borrower_id": "TEST-1",
        "evaluation_date": date(2026, 8, 31),
        "conservative_monthly_inflow": Decimal("50000"),
        "household_expense": Decimal("10000"),
        "business_expense": Decimal("25000"),
        "formal_emis": Decimal("0"),
        "informal_installments": Decimal("0"),
        "monthly_surplus": Decimal("15000"),
        "available_balance_buffer": Decimal("5000"),
        "safe_emi_min": Decimal("6000"),
        "safe_emi_max": Decimal("7500"),
        "safe_emi_max_factor": Decimal("0.5"),
        "new_credit_blocked": False,
        "repayment_status": "CURRENT",
        "insufficient_history": False,
        "cashflow_status": "SUFFICIENT",
        "overall_confidence": Decimal("0.85"),
        "stress_tests": [
            StressTestSummary(name="income_drop", passed=False, severity="HIGH")
        ],
    }
    data.update(overrides)
    return FinancialBaseline(**data)


def loan_goal(**overrides):
    data = {
        "type": "LOAN_READINESS",
        "title": "Car",
        "target_amount": Decimal("100000"),
        "deadline_months": 8,
        "annual_interest_rate": Decimal("0.14"),
        "tenure_months": 24,
    }
    data.update(overrides)
    return LoanReadinessGoal(**data)


def test_affordable_loan_is_achievable_now():
    plan = WhatIfEngine.plan(baseline(), loan_goal())
    assert plan.outcome == "ACHIEVABLE_NOW"
    assert plan.required_state.required_emi == Decimal("4801.29")
    assert plan.gap.emi_gap == 0
    assert plan.gap.monthly_cashflow_gap == 0


def test_unaffordable_loan_has_traceable_change_paths():
    plan = WhatIfEngine.plan(
        baseline(
            monthly_surplus=Decimal("6000"),
            safe_emi_min=Decimal("2400"),
            safe_emi_max=Decimal("3000"),
        ),
        loan_goal(),
    )
    assert plan.outcome == "ACHIEVABLE_WITH_CHANGES"
    assert plan.gap.monthly_cashflow_gap > 0
    mixed = next(path for path in plan.paths if path.type == "MIXED_CHANGE")
    assert mixed.expense_reduction + mixed.income_increase == plan.gap.monthly_cashflow_gap
    assert any(path.type == "LOWER_PRINCIPAL" for path in plan.paths)


def test_repayment_block_cannot_be_bypassed():
    plan = WhatIfEngine.plan(
        baseline(new_credit_blocked=True, safe_emi_min=Decimal("0"), safe_emi_max=Decimal("0")),
        loan_goal(),
    )
    assert plan.outcome == "BLOCKED"
    assert [path.type for path in plan.paths] == ["RESOLVE_REPAYMENT_BLOCK"]


def test_readiness_deadline_does_not_change_loan_emi():
    short = WhatIfEngine.plan(baseline(), loan_goal(deadline_months=2))
    long = WhatIfEngine.plan(baseline(), loan_goal(deadline_months=60))
    assert short.required_state.required_emi == long.required_state.required_emi


def test_buffer_target_is_separate_from_recurring_gap():
    plan = WhatIfEngine.plan(baseline(), loan_goal(desired_buffer=Decimal("21000")))
    assert plan.outcome == "ACHIEVABLE_WITH_CHANGES"
    assert plan.gap.buffer_gap == Decimal("16000.00")
    assert plan.gap.monthly_buffer_contribution == Decimal("2000.00")
    assert plan.gap.monthly_cashflow_gap == 0


def test_savings_uses_explicit_goal_savings_not_balance_buffer():
    goal = SavingsTargetGoal(
        type="SAVINGS_TARGET",
        title="Education",
        target_amount=Decimal("100000"),
        current_goal_savings=Decimal("0"),
        deadline_months=10,
    )
    low_buffer = WhatIfEngine.plan(baseline(available_balance_buffer=Decimal("0")), goal)
    high_buffer = WhatIfEngine.plan(baseline(available_balance_buffer=Decimal("90000")), goal)
    assert low_buffer.required_state.required_monthly_saving == Decimal("10000.00")
    assert high_buffer.required_state.required_monthly_saving == Decimal("10000.00")


def test_thin_history_returns_insufficient_data():
    plan = WhatIfEngine.plan(baseline(insufficient_history=True), loan_goal())
    assert plan.outcome == "INSUFFICIENT_DATA"
    assert plan.paths == []
    assert plan.current_state.monthly_inflow is None
    assert plan.current_state.monthly_surplus is None
    assert plan.current_state.safe_emi_max is None
    assert plan.required_state.required_monthly_surplus is None
    assert plan.gap.monthly_cashflow_gap is None
    assert "monthly_surplus" in plan.safety.missing_fields
    assert "whatIf.safety.insufficientHistory" in plan.safety.warning_keys
