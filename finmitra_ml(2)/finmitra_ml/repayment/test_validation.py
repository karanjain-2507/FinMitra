"""Step 1: explicit repayment transaction validation."""

from __future__ import annotations

from datetime import date

from common.schemas import BorrowerInput, Loan, Repayment, Transaction
from repayment.matching import SELF_DECLARED, is_digitally_matched, match_repayments


def _loan() -> Loan:
    return Loan(
        loan_id="L001",
        lender_id="LENDER-01",
        issue_date=date(2025, 12, 1),
        principal_amount=30000,
        installment_amount=5000,
        installment_frequency="MONTHLY",
        number_of_installments=6,
        first_due_date=date(2026, 1, 1),
        declared_status="CURRENT",
        relationship_type="INFORMAL",
    )


def _claim(**overrides) -> Repayment:
    payload = dict(
        repayment_id="R001",
        loan_id="L001",
        date=date(2026, 1, 1),
        amount=5000,
        transaction_id="T001",
        source="SELF_DECLARED",
        verified=False,
        confidence=0.4,
    )
    payload.update(overrides)
    return Repayment(**payload)


def _tx(**overrides) -> Transaction:
    payload = dict(
        transaction_id="T001",
        date=date(2026, 1, 1),
        amount=5000,
        direction="DEBIT",
        category="LOAN_REPAYMENT",
        counterparty_id="LENDER-01",
        description="EMI",
        source="BANK_STATEMENT",
        verified=True,
    )
    payload.update(overrides)
    return Transaction(**payload)


def _profile(tx_list, claims) -> BorrowerInput:
    return BorrowerInput(
        borrower_id="B-VAL",
        evaluation_date=date(2026, 4, 15),
        informal_loans=[_loan()],
        repayment_claims=claims,
        transactions=tx_list,
    )


class TestTransactionValidation:
    def test_valid_debit_repayment(self) -> None:
        warnings: list[str] = []
        matches = match_repayments(
            _profile([_tx()], [_claim()]),
            warnings=warnings,
        )
        digital = [match for match in matches if is_digitally_matched(match)]
        assert len(digital) == 1
        assert digital[0].transaction_id == "T001"
        assert digital[0].verified is True

    def test_credit_transaction_claimed_as_repayment(self) -> None:
        warnings: list[str] = []
        matches = match_repayments(
            _profile([_tx(direction="CREDIT")], [_claim()]),
            warnings=warnings,
        )
        assert all(match.match_method == SELF_DECLARED for match in matches)
        assert not any(is_digitally_matched(match) for match in matches)
        assert any("DEBIT" in warning for warning in warnings)

    def test_wrong_amount(self) -> None:
        warnings: list[str] = []
        matches = match_repayments(
            _profile([_tx(amount=1000)], [_claim(amount=5000)]),
            warnings=warnings,
        )
        assert all(match.match_method == SELF_DECLARED for match in matches)
        assert any("amount" in warning for warning in warnings)

    def test_zero_amount(self) -> None:
        warnings: list[str] = []
        matches = match_repayments(
            _profile([_tx(amount=0)], [_claim()]),
            warnings=warnings,
        )
        assert all(match.match_method == SELF_DECLARED for match in matches)
        assert any("positive" in warning for warning in warnings)

    def test_nonexistent_transaction(self) -> None:
        warnings: list[str] = []
        matches = match_repayments(
            _profile([], [_claim(transaction_id="T-MISSING")]),
            warnings=warnings,
        )
        assert all(match.match_method == SELF_DECLARED for match in matches)
        assert any("does not exist" in warning for warning in warnings)

    def test_transaction_reused_twice(self) -> None:
        warnings: list[str] = []
        claims = [
            _claim(repayment_id="R1"),
            _claim(repayment_id="R2"),
        ]
        matches = match_repayments(_profile([_tx()], claims), warnings=warnings)
        digital = [match for match in matches if is_digitally_matched(match)]
        declared = [match for match in matches if match.match_method == SELF_DECLARED]
        assert len(digital) == 1
        assert len(declared) == 1
        assert any("already consumed" in warning for warning in warnings)
