from dataclasses import replace

import numpy as np

from features.pipeline import FEATURE_NAMES, build_features_for_profile
from schemas import BorrowerInput


EXPECTED_FEATURES = (
    "median_monthly_business_inflow_paise",
    "inflow_volatility",
    "six_month_inflow_trend",
    "longest_inflow_gap_days",
    "median_active_earning_days",
    "income_source_concentration",
    "repeat_customer_ratio",
    "seasonality_adjusted_stability",
    "median_operating_surplus_paise",
    "negative_cashflow_month_ratio",
    "expense_volatility",
    "balance_buffer_days",
)


def test_exact_original_12_feature_contract(stable_profile):
    vector = build_features_for_profile(stable_profile)
    assert FEATURE_NAMES == EXPECTED_FEATURES
    assert tuple(vector.values) == EXPECTED_FEATURES
    assert len(vector.values) == 12


def test_defined_features_are_finite(stable_profile):
    vector = build_features_for_profile(stable_profile)
    assert all(
        value is None or np.isfinite(value)
        for value in vector.values.values()
    )


def test_original_feature_ranges(stable_profile):
    values = build_features_for_profile(stable_profile).values
    assert -2 <= values["six_month_inflow_trend"] <= 2
    assert 0 <= values["negative_cashflow_month_ratio"] <= 1
    assert 0 <= values["seasonality_adjusted_stability"] <= 1
    assert values["longest_inflow_gap_days"] >= 0
    for name in ("income_source_concentration", "repeat_customer_ratio"):
        assert values[name] is None or 0 <= values[name] <= 1


def test_duplicate_does_not_change_features(stable_profile):
    baseline = build_features_for_profile(stable_profile)
    duplicated = BorrowerInput(
        stable_profile.borrower_id,
        stable_profile.as_of_date,
        stable_profile.transactions + (stable_profile.transactions[0],),
    )
    result = build_features_for_profile(duplicated)
    assert result.values == baseline.values
    assert result.context["duplicate_count"] == 1


def test_order_invariance(stable_profile):
    baseline = build_features_for_profile(stable_profile)
    reversed_profile = BorrowerInput(
        stable_profile.borrower_id,
        stable_profile.as_of_date,
        tuple(reversed(stable_profile.transactions)),
    )
    assert build_features_for_profile(reversed_profile).values == baseline.values


def test_non_operating_credits_do_not_become_income(stable_profile):
    baseline = build_features_for_profile(stable_profile)
    template = stable_profile.transactions[0]
    additions = (
        replace(
            template,
            transaction_id="XFER",
            category="SELF_TRANSFER",
            amount_paise=99999999,
        ),
        replace(
            template,
            transaction_id="LOAN",
            category="LOAN_DISBURSEMENT",
            amount_paise=99999999,
        ),
        replace(
            template,
            transaction_id="CASH",
            category="SELF_DECLARED_CASH_INCOME",
            amount_paise=99999999,
            model_eligible=False,
            verification="SELF_DECLARED",
        ),
    )
    changed = BorrowerInput(
        stable_profile.borrower_id,
        stable_profile.as_of_date,
        stable_profile.transactions + additions,
    )
    result = build_features_for_profile(changed)
    assert (
        result.values["median_monthly_business_inflow_paise"]
        == baseline.values["median_monthly_business_inflow_paise"]
    )
    assert result.context["self_declared_income_share"] > 0


def test_balance_buffer_is_missing_without_balance_history(stable_profile):
    vector = build_features_for_profile(stable_profile)
    assert vector.values["balance_buffer_days"] is None


def test_balance_buffer_uses_balance_after_paise(stable_profile):
    with_balances = tuple(
        replace(item, balance_after_paise=2_000_000)
        for item in stable_profile.transactions
    )
    profile = BorrowerInput(
        stable_profile.borrower_id,
        stable_profile.as_of_date,
        with_balances,
    )
    assert build_features_for_profile(profile).values["balance_buffer_days"] > 0
