from dataclasses import replace

from model.inference import CashflowEngine
from schemas import BorrowerInput


def test_zero_transactions_is_insufficient(stable_profile):
    empty = BorrowerInput("EMPTY", stable_profile.as_of_date, ())
    result = CashflowEngine().assess(empty)
    assert result.status == "INSUFFICIENT"
    assert result.score is None


def test_only_transfers_is_insufficient(stable_profile):
    transfers = tuple(
        replace(item, category="SELF_TRANSFER") for item in stable_profile.transactions
    )
    result = CashflowEngine().assess(BorrowerInput("TRANSFERS", stable_profile.as_of_date, transfers))
    assert result.status == "INSUFFICIENT"
    assert result.score is None


def test_only_loan_disbursements_is_insufficient(stable_profile):
    loans = tuple(
        replace(item, category="LOAN_DISBURSEMENT", direction="CREDIT")
        for item in stable_profile.transactions
    )
    result = CashflowEngine().assess(BorrowerInput("LOANS", stable_profile.as_of_date, loans))
    assert result.status == "INSUFFICIENT"


def test_only_unverified_cash_is_insufficient(stable_profile):
    cash = tuple(
        replace(
            item, category="SELF_DECLARED_CASH_INCOME", direction="CREDIT",
            model_eligible=False, verification="SELF_DECLARED",
        )
        for item in stable_profile.transactions
    )
    result = CashflowEngine().assess(BorrowerInput("CASH", stable_profile.as_of_date, cash))
    assert result.status == "INSUFFICIENT"
    assert "UNVERIFIED_SELF_DECLARED_INCOME_EXCLUDED" in result.warnings


def test_exact_minimum_history_returns_a_score(stable_profile):
    months = sorted({item.date[:7] for item in stable_profile.transactions})[:3]
    selected = tuple(item for item in stable_profile.transactions if item.date[:7] in months)
    assert len([item for item in selected if item.category in {"BUSINESS_INCOME", "POS_SETTLEMENT", "MARKETPLACE_SETTLEMENT", "INVENTORY", "SUPPLIER_PURCHASE", "BUSINESS_UTILITY"}]) >= 30
    cutoff = max(item.date for item in selected)
    result = CashflowEngine().assess(BorrowerInput("BOUNDARY", cutoff, selected))
    assert result.status == "DEGRADED"
    assert result.score is not None


def test_huge_transaction_still_returns_a_bounded_probability(stable_profile):
    huge = replace(stable_profile.transactions[0], transaction_id="HUGE", amount_paise=10**14)
    profile = BorrowerInput("HUGE", stable_profile.as_of_date, stable_profile.transactions + (huge,))
    result = CashflowEngine().assess(profile)
    assert result.score is not None
    assert result.stress_probability is not None
    assert 0 <= result.stress_probability <= 1
    assert abs(result.score - 100 * (1 - result.stress_probability)) <= 0.001
