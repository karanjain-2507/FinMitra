"""Safer loan-to-transaction matching tests."""

from __future__ import annotations

from datetime import date

from common.schemas import BorrowerInput, Loan, Repayment, Transaction
from repayment.matching import (
    COUNTERPARTY_MATCH,
    EXPLICIT_LOAN_ID,
    is_digitally_matched,
    match_repayments,
)

LENDER = "SUPPLIER-01"


def _loan() -> Loan:
    return Loan(
        loan_id="L-SUPPLIER",
        lender_id=LENDER,
        issue_date=date(2025, 12, 1),
        principal_amount=30000,
        installment_amount=5000,
        installment_frequency="MONTHLY",
        number_of_installments=6,
        first_due_date=date(2026, 1, 1),
        declared_status="CURRENT",
        relationship_type="SUPPLIER",
    )


def _tx(**overrides) -> Transaction:
    payload = dict(
        transaction_id="T-001",
        date=date(2026, 1, 1),
        amount=5000,
        direction="DEBIT",
        category="LOAN_REPAYMENT",
        counterparty_id=LENDER,
        description="EMI",
        source="BANK_STATEMENT",
        verified=True,
    )
    payload.update(overrides)
    return Transaction(**payload)


def _profile(transactions: list[Transaction], claims: list[Repayment] | None = None) -> BorrowerInput:
    return BorrowerInput(
        borrower_id="B-MATCH",
        evaluation_date=date(2026, 4, 15),
        informal_loans=[_loan()],
        repayment_claims=claims or [],
        transactions=transactions,
    )


def _digital_matches(profile: BorrowerInput):
    return [match for match in match_repayments(profile) if is_digitally_matched(match)]


class TestSaferLoanTransactionMatching:
    def test_lender_repayment_category_compatible_amount_and_date_can_match(self) -> None:
        matches = _digital_matches(
            _profile([_tx(category="LOAN_REPAYMENT", amount=5000, date=date(2026, 1, 1))])
        )
        assert len(matches) == 1
        assert matches[0].transaction_id == "T-001"
        assert matches[0].loan_id == "L-SUPPLIER"
        assert matches[0].match_method == COUNTERPARTY_MATCH

    def test_lender_purchase_category_does_not_automatically_match(self) -> None:
        matches = _digital_matches(
            _profile(
                [
                    _tx(
                        category="PURCHASE",
                        amount=5000,
                        date=date(2026, 1, 1),
                        description="Inventory restock",
                    )
                ]
            )
        )
        assert matches == []

    def test_lender_incompatible_amount_does_not_match(self) -> None:
        matches = _digital_matches(
            _profile(
                [
                    _tx(
                        category="LOAN_REPAYMENT",
                        amount=18500,
                        date=date(2026, 1, 1),
                    )
                ]
            )
        )
        assert matches == []

    def test_unrelated_supplier_transaction_does_not_count_as_repayment(self) -> None:
        matches = _digital_matches(
            _profile(
                [
                    _tx(
                        transaction_id="T-GOODS",
                        category="PURCHASE",
                        amount=1200,
                        date=date(2026, 1, 20),
                        description="Weekly goods purchase",
                    )
                ]
            )
        )
        assert matches == []

    def test_strong_explicit_transaction_match_still_works(self) -> None:
        profile = _profile(
            transactions=[_tx(transaction_id="T-EXPLICIT")],
            claims=[
                Repayment(
                    repayment_id="R-EXPLICIT",
                    loan_id="L-SUPPLIER",
                    date=date(2026, 1, 1),
                    amount=5000,
                    transaction_id="T-EXPLICIT",
                    source="BANK_STATEMENT",
                    verified=True,
                    confidence=0.95,
                )
            ],
        )
        matches = match_repayments(profile)
        digital = [match for match in matches if is_digitally_matched(match)]
        assert len(digital) == 1
        assert digital[0].match_method == EXPLICIT_LOAN_ID
        assert digital[0].transaction_id == "T-EXPLICIT"
        assert digital[0].repayment_id == "R-EXPLICIT"
        assert digital[0].match_confidence >= 0.88
