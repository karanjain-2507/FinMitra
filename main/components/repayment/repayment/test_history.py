"""Supplier confirmation availability and empty loan history."""

from __future__ import annotations

from datetime import date

from common.schemas import BorrowerInput, Loan, Repayment, Transaction
from repayment.engine import assess
from repayment.test_engine import load_fixture


def test_supplier_relationship_without_confirmation_is_not_confirmed() -> None:
    result = assess(load_fixture("strong_borrower.json"))
    assert result.features["digitally_matched_repayment_ratio"] == 1.0
    assert result.features["supplier_confirmation_available"] is False
    assert result.features["supplier_confirmed_repayment_ratio"] is None
    assert any("Supplier confirmation is unavailable" in warning for warning in result.warnings)
    assert not any(reason.code == "RP09" for reason in result.reasons)


def test_explicit_supplier_confirmation_is_counted() -> None:
    profile = load_fixture("strong_borrower.json")
    loans = []
    for loan in profile.informal_loans:
        loans.append(loan.model_copy(update={"supplier_confirmed": True}))
    profile = profile.model_copy(update={"informal_loans": loans})
    result = assess(profile)
    assert result.features["supplier_confirmation_available"] is True
    assert result.features["supplier_confirmed_repayment_ratio"] == 1.0
    assert any(reason.code == "RP09" for reason in result.reasons)


def test_no_prior_loans_is_not_thin_file() -> None:
    result = assess(
        BorrowerInput(
            borrower_id="B-NONE",
            evaluation_date=date(2026, 4, 15),
            informal_loans=[],
            repayment_claims=[],
            transactions=[],
        )
    )
    assert result.features["no_prior_loans"] is True
    assert result.status != "INSUFFICIENT_EVIDENCE"
    assert result.status == "CURRENT"
    assert result.new_credit_blocked is False
    assert any("No prior loans" in warning for warning in result.warnings)


def test_missing_repayment_evidence_is_insufficient() -> None:
    result = assess(load_fixture("thin_file.json"))
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.features["no_prior_loans"] is False


def test_normal_repayment_history() -> None:
    result = assess(load_fixture("strong_borrower.json"))
    assert result.status == "COMPLETED"
    assert result.features["total_loans_declared"] == 1
    assert result.features["completed_credit_cycles"] == 1
    assert any(reason.code == "RP04" for reason in result.reasons)
