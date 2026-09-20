"""Digitally matched ratio and actual contradictions."""

from __future__ import annotations

from datetime import date

from common.schemas import BorrowerInput, Loan, Repayment, Transaction
from repayment.engine import assess


def _loan(**overrides) -> Loan:
    payload = dict(
        loan_id="L-MIX",
        lender_id="L1",
        issue_date=date(2025, 12, 1),
        principal_amount=30000,
        installment_amount=5000,
        installment_frequency="MONTHLY",
        number_of_installments=6,
        first_due_date=date(2026, 1, 1),
        declared_status="CURRENT",
        relationship_type="INFORMAL",
    )
    payload.update(overrides)
    return Loan(**payload)


def test_self_declared_without_contradiction() -> None:
    result = assess(
        BorrowerInput(
            borrower_id="B-SELF",
            evaluation_date=date(2026, 4, 15),
            informal_loans=[_loan()],
            repayment_claims=[
                Repayment(
                    repayment_id="R-SELF",
                    loan_id="L-MIX",
                    date=date(2026, 1, 1),
                    amount=5000,
                    transaction_id=None,
                    source="SELF_DECLARED",
                    verified=False,
                    confidence=0.2,
                )
            ],
            transactions=[],
        )
    )
    assert result.features["contradictory_declarations"] == 0
    assert result.features["self_declared_repayment_amount"] == 5000
    assert result.features["total_amount_repaid"] == 0
    assert result.confidence < 0.6
    assert not any(reason.code == "RP08" for reason in result.reasons)


def test_actual_contradictory_repayment_claim() -> None:
    result = assess(
        BorrowerInput(
            borrower_id="B-BAD-TX",
            evaluation_date=date(2026, 4, 15),
            informal_loans=[_loan()],
            repayment_claims=[
                Repayment(
                    repayment_id="R-BAD",
                    loan_id="L-MIX",
                    date=date(2026, 1, 1),
                    amount=5000,
                    transaction_id="T-CREDIT",
                    source="SELF_DECLARED",
                    verified=False,
                    confidence=0.4,
                )
            ],
            transactions=[
                Transaction(
                    transaction_id="T-CREDIT",
                    date=date(2026, 1, 1),
                    amount=5000,
                    direction="CREDIT",
                    category="LOAN_DISBURSEMENT",
                    counterparty_id="L1",
                    source="BANK_STATEMENT",
                    verified=True,
                )
            ],
        )
    )
    assert result.features["contradictory_declarations"] > 0
    assert any(reason.code == "RP08" for reason in result.reasons)


def test_mixed_digital_and_self_declared_ratio() -> None:
    result = assess(
        BorrowerInput(
            borrower_id="B-MIX",
            evaluation_date=date(2026, 4, 15),
            informal_loans=[_loan()],
            repayment_claims=[
                Repayment(
                    repayment_id="R-DIG",
                    loan_id="L-MIX",
                    date=date(2026, 1, 1),
                    amount=8000,
                    transaction_id="T-DIG",
                    source="BANK_STATEMENT",
                    verified=True,
                    confidence=0.9,
                ),
                Repayment(
                    repayment_id="R-SELF",
                    loan_id="L-MIX",
                    date=date(2026, 2, 1),
                    amount=2000,
                    transaction_id=None,
                    source="SELF_DECLARED",
                    verified=False,
                    confidence=0.2,
                ),
            ],
            transactions=[
                Transaction(
                    transaction_id="T-DIG",
                    date=date(2026, 1, 1),
                    amount=8000,
                    direction="DEBIT",
                    category="LOAN_REPAYMENT",
                    counterparty_id="L1",
                    source="BANK_STATEMENT",
                    verified=True,
                )
            ],
        )
    )
    assert result.features["digitally_matched_repayment_ratio"] == 0.8
    assert result.features["digitally_matched_repayment_ratio"] != 1.0
    assert result.features["self_declared_repayment_amount"] == 2000
    assert result.features["total_amount_repaid"] == 8000
    assert result.features["contradictory_declarations"] == 0
    assert not any(reason.code == "RP08" for reason in result.reasons)
