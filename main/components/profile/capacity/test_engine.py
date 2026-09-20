"""
capacity/test_engine.py

Comprehensive unit tests for the Capacity Engine.

Tests cover:
  - Monthly surplus calculation
  - Safe EMI range
  - Negative surplus handling
  - Policy factor validation
  - Hard repayment block
  - EMI formula
  - Maximum principal
  - Requested-loan assessment
  - Stress tests
  - Status determination
  - Confidence calculation
  - Full engine integration
"""
from __future__ import annotations

import math
import pytest

from common.config import DEFAULT_POLICY
from common.schemas import CapacityInput, CapacityPolicy
from capacity.calculations import (
    assess_requested_loan,
    compute_confidence,
    compute_emi,
    compute_max_principal,
    compute_max_principal_table,
    compute_monthly_surplus,
    compute_safe_emi,
    determine_status,
    zero_safe_emi,
)
from capacity.engine import CapacityEngine
from capacity.stress_tests import (
    run_all_stress_tests,
    stress_expense_increase_30pct,
    stress_existing_informal_continues,
    stress_income_drop_20pct,
    stress_seasonal_low_income,
    stress_zero_income_month,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_input() -> CapacityInput:
    """Standard test borrower: ₹28,000 inflow, ₹17,500 essential, ₹2,500 obligations."""
    return CapacityInput(
        conservative_monthly_inflow=28000,
        essential_household_expense=10000,
        essential_business_expense=7500,
        existing_formal_emis=1500,
        existing_informal_installments=1000,
        income_volatility=0.18,
        lowest_recent_monthly_inflow=21000,
        available_balance_buffer=12000,
        outstanding_delinquent_amount=0,
    )


@pytest.fixture
def loan_input() -> CapacityInput:
    """Same as base_input but with a specific loan request."""
    return CapacityInput(
        conservative_monthly_inflow=28000,
        essential_household_expense=10000,
        essential_business_expense=7500,
        existing_formal_emis=1500,
        existing_informal_installments=1000,
        income_volatility=0.18,
        lowest_recent_monthly_inflow=21000,
        available_balance_buffer=12000,
        outstanding_delinquent_amount=0,
        requested_loan_amount=40000,
        annual_interest_rate=0.14,
        tenure_months=12,
    )


@pytest.fixture
def negative_surplus_input() -> CapacityInput:
    """Borrower where expenses exceed income."""
    return CapacityInput(
        conservative_monthly_inflow=20000,
        essential_household_expense=12000,
        essential_business_expense=8000,
        existing_formal_emis=3000,
        existing_informal_installments=0,
        income_volatility=0.20,
        lowest_recent_monthly_inflow=15000,
        available_balance_buffer=5000,
        outstanding_delinquent_amount=0,
    )


@pytest.fixture
def delinquent_input() -> CapacityInput:
    """Strong income borrower with delinquent amount."""
    return CapacityInput(
        conservative_monthly_inflow=35000,
        essential_household_expense=12000,
        essential_business_expense=8000,
        existing_formal_emis=0,
        existing_informal_installments=3000,
        income_volatility=0.10,
        lowest_recent_monthly_inflow=28000,
        available_balance_buffer=8000,
        outstanding_delinquent_amount=25000,
    )


# ============================================================================
# Monthly surplus tests
# ============================================================================

class TestMonthlySurplus:
    def test_positive_surplus(self, base_input):
        surplus = compute_monthly_surplus(base_input)
        # 28000 - 10000 - 7500 - 1500 - 1000 = 8000
        assert surplus == pytest.approx(8000.0)

    def test_zero_surplus(self):
        inp = CapacityInput(
            conservative_monthly_inflow=20000,
            essential_household_expense=10000,
            essential_business_expense=7000,
            existing_formal_emis=2000,
            existing_informal_installments=1000,
            income_volatility=0.15,
            lowest_recent_monthly_inflow=15000,
            available_balance_buffer=2000,
            outstanding_delinquent_amount=0,
        )
        surplus = compute_monthly_surplus(inp)
        assert surplus == pytest.approx(0.0)

    def test_negative_surplus(self, negative_surplus_input):
        surplus = compute_monthly_surplus(negative_surplus_input)
        # 20000 - 12000 - 8000 - 3000 - 0 = -3000
        assert surplus == pytest.approx(-3000.0)

    def test_formal_emis_only(self):
        inp = CapacityInput(
            conservative_monthly_inflow=25000,
            essential_household_expense=8000,
            essential_business_expense=6000,
            existing_formal_emis=3000,
            existing_informal_installments=0,
            income_volatility=0.10,
            lowest_recent_monthly_inflow=20000,
            available_balance_buffer=5000,
            outstanding_delinquent_amount=0,
        )
        surplus = compute_monthly_surplus(inp)
        assert surplus == pytest.approx(8000.0)  # 25000-8000-6000-3000-0

    def test_informal_installments_only(self):
        inp = CapacityInput(
            conservative_monthly_inflow=25000,
            essential_household_expense=8000,
            essential_business_expense=6000,
            existing_formal_emis=0,
            existing_informal_installments=3000,
            income_volatility=0.10,
            lowest_recent_monthly_inflow=20000,
            available_balance_buffer=5000,
            outstanding_delinquent_amount=0,
        )
        surplus = compute_monthly_surplus(inp)
        assert surplus == pytest.approx(8000.0)

    def test_both_obligations(self):
        inp = CapacityInput(
            conservative_monthly_inflow=25000,
            essential_household_expense=8000,
            essential_business_expense=6000,
            existing_formal_emis=2000,
            existing_informal_installments=1000,
            income_volatility=0.10,
            lowest_recent_monthly_inflow=20000,
            available_balance_buffer=5000,
            outstanding_delinquent_amount=0,
        )
        surplus = compute_monthly_surplus(inp)
        assert surplus == pytest.approx(8000.0)


# ============================================================================
# Safe EMI tests
# ============================================================================

class TestSafeEMI:
    def test_positive_surplus_default_policy(self, base_input):
        surplus = compute_monthly_surplus(base_input)  # 8000
        safe_emi = compute_safe_emi(surplus, DEFAULT_POLICY)
        assert safe_emi.minimum == pytest.approx(3200.0)  # 8000 * 0.40
        assert safe_emi.maximum == pytest.approx(4000.0)  # 8000 * 0.50

    def test_negative_surplus_gives_zero_emi(self, negative_surplus_input):
        surplus = compute_monthly_surplus(negative_surplus_input)
        assert surplus < 0
        safe_emi = compute_safe_emi(surplus, DEFAULT_POLICY)
        assert safe_emi.minimum == 0.0
        assert safe_emi.maximum == 0.0

    def test_zero_surplus_gives_zero_emi(self):
        safe_emi = compute_safe_emi(0.0, DEFAULT_POLICY)
        assert safe_emi.minimum == 0.0
        assert safe_emi.maximum == 0.0

    def test_custom_policy_factors(self):
        policy = CapacityPolicy(safe_emi_min_factor=0.30, safe_emi_max_factor=0.60)
        safe_emi = compute_safe_emi(10000.0, policy)
        assert safe_emi.minimum == pytest.approx(3000.0)
        assert safe_emi.maximum == pytest.approx(6000.0)

    def test_40_percent_factor(self):
        safe_emi = compute_safe_emi(10000.0, DEFAULT_POLICY)
        assert safe_emi.minimum == pytest.approx(4000.0)

    def test_50_percent_factor(self):
        safe_emi = compute_safe_emi(10000.0, DEFAULT_POLICY)
        assert safe_emi.maximum == pytest.approx(5000.0)

    def test_invalid_policy_min_greater_than_max(self):
        with pytest.raises(Exception):
            CapacityPolicy(safe_emi_min_factor=0.60, safe_emi_max_factor=0.40)

    def test_policy_factors_out_of_range(self):
        with pytest.raises(Exception):
            CapacityPolicy(safe_emi_min_factor=-0.1, safe_emi_max_factor=0.50)
        with pytest.raises(Exception):
            CapacityPolicy(safe_emi_min_factor=0.40, safe_emi_max_factor=1.5)

    def test_zero_safe_emi_helper(self):
        emi = zero_safe_emi()
        assert emi.minimum == 0.0
        assert emi.maximum == 0.0


# ============================================================================
# Hard repayment block tests
# ============================================================================

class TestHardBlock:
    def test_blocked_strong_income_yields_zero_emi(self, delinquent_input):
        """Strong income + new_credit_blocked → safe EMI must be ₹0."""
        result = CapacityEngine.assess(
            inp=delinquent_input,
            new_credit_blocked=True,
        )
        assert result.safe_emi.minimum == 0.0
        assert result.safe_emi.maximum == 0.0
        assert result.status == "BLOCKED"

    def test_not_blocked_normal_calculation(self, base_input):
        result = CapacityEngine.assess(inp=base_input, new_credit_blocked=False)
        assert result.safe_emi.maximum > 0
        assert result.status != "BLOCKED"

    def test_blocked_reason_is_present(self, delinquent_input):
        result = CapacityEngine.assess(inp=delinquent_input, new_credit_blocked=True)
        codes = [r.code for r in result.reasons]
        assert "CP04" in codes

    def test_blocked_max_principal_is_zero(self, delinquent_input):
        result = CapacityEngine.assess(inp=delinquent_input, new_credit_blocked=True)
        for key, val in result.max_principal.items():
            assert val == 0.0, f"max_principal[{key}] should be 0 when blocked"


# ============================================================================
# EMI calculation tests
# ============================================================================

class TestEMICalculation:
    def test_positive_interest(self):
        # P=100000, r=12%/yr, n=12 months
        emi = compute_emi(100000, 0.12, 12)
        # Standard formula: ~8884.88
        assert emi == pytest.approx(8884.88, rel=1e-3)

    def test_zero_interest(self):
        emi = compute_emi(12000, 0.0, 12)
        assert emi == pytest.approx(1000.0)

    def test_single_month(self):
        emi = compute_emi(5000, 0.12, 1)
        # Full principal + one month interest
        expected = 5000 * (0.12 / 12) * (1 + 0.12 / 12) / ((1 + 0.12 / 12) - 1)
        assert emi == pytest.approx(expected, rel=1e-6)

    def test_invalid_principal(self):
        with pytest.raises(ValueError):
            compute_emi(0, 0.12, 12)
        with pytest.raises(ValueError):
            compute_emi(-1000, 0.12, 12)

    def test_invalid_tenure(self):
        with pytest.raises(ValueError):
            compute_emi(10000, 0.12, 0)
        with pytest.raises(ValueError):
            compute_emi(10000, 0.12, -5)

    def test_invalid_interest_rate(self):
        with pytest.raises(ValueError):
            compute_emi(10000, -0.01, 12)


# ============================================================================
# Maximum principal tests
# ============================================================================

class TestMaxPrincipal:
    def test_6_months_zero_interest(self):
        # safe_emi_max=5000, rate=0%, n=6 → P = 5000*6 = 30000
        p = compute_max_principal(5000, 0.0, 6)
        assert p == pytest.approx(30000.0)

    def test_12_months_zero_interest(self):
        p = compute_max_principal(5000, 0.0, 12)
        assert p == pytest.approx(60000.0)

    def test_18_months_zero_interest(self):
        p = compute_max_principal(5000, 0.0, 18)
        assert p == pytest.approx(90000.0)

    def test_positive_interest_shorter_tenure_lower_principal(self):
        # Higher interest → lower principal for same EMI and tenure
        p_low_rate = compute_max_principal(4000, 0.08, 12)
        p_high_rate = compute_max_principal(4000, 0.24, 12)
        assert p_high_rate < p_low_rate

    def test_zero_safe_emi_yields_zero_principal(self):
        p = compute_max_principal(0.0, 0.14, 12)
        assert p == 0.0

    def test_max_principal_table_keys(self):
        table = compute_max_principal_table(4000, 0.14, [6, 12, 18])
        assert set(table.keys()) == {"6_months", "12_months", "18_months"}

    def test_max_principal_table_ordering(self):
        """Longer tenure → higher max principal (for positive interest)."""
        table = compute_max_principal_table(4000, 0.14, [6, 12, 18])
        assert table["6_months"] < table["12_months"] < table["18_months"]

    def test_round_trip_emi_to_principal(self):
        """Compute principal from EMI and verify the EMI formula is consistent."""
        original_emi = 3500.0
        rate = 0.14
        n = 12
        principal = compute_max_principal(original_emi, rate, n)
        recovered_emi = compute_emi(principal, rate, n)
        assert recovered_emi == pytest.approx(original_emi, rel=1e-6)


# ============================================================================
# Requested loan assessment tests
# ============================================================================

class TestRequestedLoanAssessment:
    def test_emi_within_capacity(self, loan_input):
        from common.schemas import SafeEMI
        safe_emi = SafeEMI(minimum=3200, maximum=4000)
        # EMI for ₹40,000 @ 14% for 12 months ≈ ₹3,592
        assessment = assess_requested_loan(loan_input, safe_emi)
        assert assessment is not None
        # EMI ~3592 < 4000 → within capacity
        assert assessment.within_safe_capacity is True
        assert assessment.emi_headroom > 0

    def test_emi_exceeds_capacity(self):
        inp = CapacityInput(
            conservative_monthly_inflow=28000,
            essential_household_expense=10000,
            essential_business_expense=7500,
            existing_formal_emis=1500,
            existing_informal_installments=1000,
            income_volatility=0.18,
            lowest_recent_monthly_inflow=21000,
            available_balance_buffer=12000,
            outstanding_delinquent_amount=0,
            requested_loan_amount=200000,
            annual_interest_rate=0.14,
            tenure_months=12,
        )
        from common.schemas import SafeEMI
        safe_emi = SafeEMI(minimum=3200, maximum=4000)
        assessment = assess_requested_loan(inp, safe_emi)
        assert assessment is not None
        assert assessment.within_safe_capacity is False
        assert assessment.emi_headroom < 0

    def test_emi_exactly_at_max(self):
        """EMI exactly at safe max → within capacity."""
        # Find a principal whose EMI = 4000 @ 14% / 12
        rate = 0.14
        n = 12
        principal = compute_max_principal(4000.0, rate, n)
        inp = CapacityInput(
            conservative_monthly_inflow=28000,
            essential_household_expense=10000,
            essential_business_expense=7500,
            existing_formal_emis=1500,
            existing_informal_installments=1000,
            income_volatility=0.18,
            lowest_recent_monthly_inflow=21000,
            available_balance_buffer=12000,
            outstanding_delinquent_amount=0,
            requested_loan_amount=principal,
            annual_interest_rate=rate,
            tenure_months=n,
        )
        from common.schemas import SafeEMI
        safe_emi = SafeEMI(minimum=3200, maximum=4000)
        assessment = assess_requested_loan(inp, safe_emi)
        assert assessment.within_safe_capacity is True
        assert abs(assessment.emi_headroom) < 0.01  # essentially 0

    def test_no_loan_returns_none(self, base_input):
        from common.schemas import SafeEMI
        safe_emi = SafeEMI(minimum=3200, maximum=4000)
        assert assess_requested_loan(base_input, safe_emi) is None


# ============================================================================
# Stress test tests
# ============================================================================

class TestStressTests:
    def test_income_drop_produces_lower_emi(self, base_input):
        surplus = compute_monthly_surplus(base_input)
        emi = compute_safe_emi(surplus, DEFAULT_POLICY)
        result = stress_income_drop_20pct(
            base_input, DEFAULT_POLICY, surplus, emi.maximum
        )
        assert result.stressed_monthly_surplus < result.baseline_monthly_surplus
        assert result.stressed_safe_emi_max <= result.baseline_safe_emi_max
        assert result.name == "income_drop_20pct"

    def test_zero_income_month_checks_buffer(self, base_input):
        surplus = compute_monthly_surplus(base_input)
        emi = compute_safe_emi(surplus, DEFAULT_POLICY)
        result = stress_zero_income_month(
            base_input, DEFAULT_POLICY, surplus, emi.maximum
        )
        # base_input buffer=12000, monthly obligations=10000+7500+1500+1000=20000
        # deficit at zero income = 20000 (all expenses + EMIs)
        # 12000 < 20000 → cannot absorb → should fail
        assert result.passed is False
        assert result.stressed_monthly_surplus < 0

    def test_expense_increase_reduces_surplus(self, base_input):
        surplus = compute_monthly_surplus(base_input)
        emi = compute_safe_emi(surplus, DEFAULT_POLICY)
        result = stress_expense_increase_30pct(
            base_input, DEFAULT_POLICY, surplus, emi.maximum
        )
        assert result.stressed_monthly_surplus < result.baseline_monthly_surplus

    def test_informal_continues_is_baseline(self, base_input):
        """ST4 should show the baseline surplus (no new shock)."""
        surplus = compute_monthly_surplus(base_input)
        emi = compute_safe_emi(surplus, DEFAULT_POLICY)
        result = stress_existing_informal_continues(
            base_input, DEFAULT_POLICY, surplus, emi.maximum
        )
        assert result.stressed_monthly_surplus == pytest.approx(surplus)
        assert result.name == "informal_installment_continues"

    def test_seasonal_low_income(self, base_input):
        surplus = compute_monthly_surplus(base_input)
        emi = compute_safe_emi(surplus, DEFAULT_POLICY)
        result = stress_seasonal_low_income(
            base_input, DEFAULT_POLICY, surplus, emi.maximum
        )
        # lowest_recent_monthly_inflow=21000 → stressed surplus = 21000-10000-7500-2500=1000
        assert result.stressed_monthly_surplus == pytest.approx(1000.0)
        assert result.name == "seasonal_low_income"

    def test_all_five_tests_run(self, base_input):
        surplus = compute_monthly_surplus(base_input)
        emi = compute_safe_emi(surplus, DEFAULT_POLICY)
        results = run_all_stress_tests(base_input, DEFAULT_POLICY, surplus, emi.maximum)
        assert len(results) == 5
        names = [r.name for r in results]
        assert "income_drop_20pct" in names
        assert "zero_income_month" in names
        assert "expense_increase_30pct" in names
        assert "informal_installment_continues" in names
        assert "seasonal_low_income" in names

    def test_stress_test_reasons_are_non_empty(self, base_input):
        surplus = compute_monthly_surplus(base_input)
        emi = compute_safe_emi(surplus, DEFAULT_POLICY)
        results = run_all_stress_tests(base_input, DEFAULT_POLICY, surplus, emi.maximum)
        for r in results:
            assert len(r.reasons) > 0, f"Stress test {r.name} has no reasons"

    def test_severity_values_are_valid(self, base_input):
        surplus = compute_monthly_surplus(base_input)
        emi = compute_safe_emi(surplus, DEFAULT_POLICY)
        results = run_all_stress_tests(base_input, DEFAULT_POLICY, surplus, emi.maximum)
        for r in results:
            assert r.severity in ("LOW", "MEDIUM", "HIGH")


# ============================================================================
# Status determination tests
# ============================================================================

class TestStatusDetermination:
    def test_sufficient_capacity(self):
        status = determine_status(8000, 4000, False, True, DEFAULT_POLICY)
        assert status == "SUFFICIENT_CAPACITY"

    def test_limited_capacity(self):
        status = determine_status(5000, 2500, False, True, DEFAULT_POLICY)
        assert status == "LIMITED_CAPACITY"  # 2500 < 3000 threshold

    def test_no_capacity_zero_surplus(self):
        status = determine_status(0, 0, False, True, DEFAULT_POLICY)
        assert status == "NO_CAPACITY"

    def test_no_capacity_negative_surplus(self):
        status = determine_status(-1000, 0, False, True, DEFAULT_POLICY)
        assert status == "NO_CAPACITY"

    def test_blocked(self):
        status = determine_status(8000, 0, True, True, DEFAULT_POLICY)
        assert status == "BLOCKED"

    def test_insufficient_data(self):
        status = determine_status(8000, 4000, False, False, DEFAULT_POLICY)
        assert status == "INSUFFICIENT_DATA"

    def test_blocked_takes_priority_over_no_data(self):
        # BLOCKED takes priority over INSUFFICIENT_DATA? No — insufficient data takes top priority
        status = determine_status(8000, 4000, True, False, DEFAULT_POLICY)
        assert status == "INSUFFICIENT_DATA"


# ============================================================================
# Full engine integration tests
# ============================================================================

class TestCapacityEngineIntegration:
    def test_strong_borrower_full_result(self, base_input):
        result = CapacityEngine.assess(base_input)
        assert result.component == "capacity"
        assert result.score is None  # always None
        assert result.status in (
            "SUFFICIENT_CAPACITY", "LIMITED_CAPACITY", "NO_CAPACITY",
            "BLOCKED", "INSUFFICIENT_DATA"
        )
        assert 0.0 <= result.confidence <= 1.0
        assert result.safe_emi.minimum >= 0
        assert result.safe_emi.maximum >= 0
        assert result.safe_emi.minimum <= result.safe_emi.maximum
        assert len(result.stress_tests) == 5
        assert isinstance(result.features, dict)
        assert "monthly_surplus" in result.features

    def test_score_is_always_none(self, base_input, loan_input, negative_surplus_input):
        for inp in (base_input, loan_input, negative_surplus_input):
            result = CapacityEngine.assess(inp)
            assert result.score is None

    def test_max_principal_keys(self, base_input):
        result = CapacityEngine.assess(base_input)
        assert set(result.max_principal.keys()) == {"6_months", "12_months", "18_months"}

    def test_requested_loan_present_when_provided(self, loan_input):
        result = CapacityEngine.assess(loan_input)
        assert result.requested_loan is not None
        assert result.requested_loan.principal == 40000

    def test_requested_loan_absent_when_not_provided(self, base_input):
        result = CapacityEngine.assess(base_input)
        assert result.requested_loan is None

    def test_version_is_set(self, base_input):
        result = CapacityEngine.assess(base_input)
        assert result.version == "1.0"

    def test_custom_policy_respected(self, base_input):
        custom_policy = CapacityPolicy(safe_emi_min_factor=0.30, safe_emi_max_factor=0.60)
        result = CapacityEngine.assess(base_input, policy=custom_policy)
        # surplus = 8000, max factor = 0.60 → safe_emi_max = 4800
        assert result.safe_emi.maximum == pytest.approx(4800.0)
        assert result.safe_emi.minimum == pytest.approx(2400.0)

    def test_no_nan_in_output(self, base_input):
        """Verify no NaN values appear anywhere in the result."""
        result = CapacityEngine.assess(base_input)
        result_dict = result.model_dump()
        _check_no_nan(result_dict)

    def test_delinquent_amount_in_warnings(self, delinquent_input):
        result = CapacityEngine.assess(delinquent_input, new_credit_blocked=False)
        has_delinquency_warning = any(
            "DELINQUENCY" in w or "delinquent" in w.lower()
            for w in result.warnings
        )
        assert has_delinquency_warning


def _check_no_nan(obj, path=""):
    """Recursively check that no NaN or Infinity values appear in a nested dict/list."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            _check_no_nan(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _check_no_nan(v, f"{path}[{i}]")
    elif isinstance(obj, float):
        assert math.isfinite(obj), f"NaN or Infinity found at {path}: {obj}"
