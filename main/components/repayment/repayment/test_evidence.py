"""Digitally matched vs verified vs self-declared evidence."""

from __future__ import annotations

from datetime import date

from common.schemas import BorrowerInput, Loan, Repayment, Transaction
from repayment.engine import assess
from repayment.matching import (
    SELF_DECLARED,
    is_digitally_matched,
    is_verified_match,
    match_repayments,
)


def _loan() -> Loan:
    return Loan(
        loan_id="L001",
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


def _profile(verified: bool | None, *, self_declared: bool = False) -> BorrowerInput:
    if self_declared:
        return BorrowerInput(
            borrower_id="B-EV",
            evaluation_date=date(2026, 4, 15),
            informal_loans=[_loan()],
            repayment_claims=[
                Repayment(
                    repayment_id="R1",
                    loan_id="L001",
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
    return BorrowerInput(
        borrower_id="B-EV",
        evaluation_date=date(2026, 4, 15),
        informal_loans=[_loan()],
        repayment_claims=[
            Repayment(
                repayment_id="R1",
                loan_id="L001",
                date=date(2026, 1, 1),
                amount=5000,
                transaction_id="T1",
                source="BANK_STATEMENT",
                verified=False,
                confidence=0.5,
            )
        ],
        transactions=[
            Transaction(
                transaction_id="T1",
                date=date(2026, 1, 1),
                amount=5000,
                direction="DEBIT",
                category="LOAN_REPAYMENT",
                counterparty_id="L1",
                source="BANK_STATEMENT",
                verified=verified,
            )
        ],
    )


class TestEvidenceClassification:
    def test_verified_digital_repayment(self) -> None:
        matches = match_repayments(_profile(True))
        digital = [match for match in matches if is_digitally_matched(match)]
        assert len(digital) == 1
        assert digital[0].verified is True
        assert is_verified_match(digital[0])
        assert digital[0].match_confidence >= 0.9

    def test_matched_but_unverified_repayment(self) -> None:
        matches = match_repayments(_profile(False))
        digital = [match for match in matches if is_digitally_matched(match)]
        assert len(digital) == 1
        assert digital[0].verified is False
        assert not is_verified_match(digital[0])
        assert digital[0].match_confidence < 0.9

    def test_self_declared_repayment(self) -> None:
        matches = match_repayments(_profile(None, self_declared=True))
        assert matches
        assert all(match.match_method == SELF_DECLARED for match in matches)
        assert not any(is_digitally_matched(match) for match in matches)
        assert not any(is_verified_match(match) for match in matches)

    def test_confidence_verified_gt_matched_gt_self_declared(self) -> None:
        verified = assess(_profile(True)).confidence
        unmatched = assess(_profile(False)).confidence
        declared = assess(_profile(None, self_declared=True)).confidence
        assert verified > unmatched > declared
