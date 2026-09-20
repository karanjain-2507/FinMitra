"""Deterministic repayment status rules."""

from __future__ import annotations

from datetime import date

from common.schemas import BorrowerInput, Loan, Repayment, Transaction
from repayment.engine import assess
from repayment.test_engine import load_fixture


def _base_loan(**overrides) -> Loan:
    payload = dict(
        loan_id="L-STATUS",
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


def _paid_tx(index: int, day: date) -> tuple[Repayment, Transaction]:
    tid = f"T{index}"
    rid = f"R{index}"
    claim = Repayment(
        repayment_id=rid,
        loan_id="L-STATUS",
        date=day,
        amount=5000,
        transaction_id=tid,
        source="BANK_STATEMENT",
        verified=True,
        confidence=0.9,
    )
    tx = Transaction(
        transaction_id=tid,
        date=day,
        amount=5000,
        direction="DEBIT",
        category="LOAN_REPAYMENT",
        counterparty_id="L1",
        source="BANK_STATEMENT",
        verified=True,
    )
    return claim, tx


class TestStatusRules:
    def test_current_borrower(self) -> None:
        result = assess(load_fixture("seasonal_business.json"))
        assert result.status == "CURRENT"
        assert result.new_credit_blocked is False

    def test_recent_missed_installment_is_behind_schedule(self) -> None:
        claims, txs = [], []
        for i, day in enumerate(
            [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)], start=1
        ):
            claim, tx = _paid_tx(i, day)
            claims.append(claim)
            txs.append(tx)
        profile = BorrowerInput(
            borrower_id="B-RECENT",
            evaluation_date=date(2026, 4, 10),
            informal_loans=[_base_loan()],
            repayment_claims=claims,
            transactions=txs,
        )
        result = assess(profile)
        assert result.status == "BEHIND_SCHEDULE"
        assert result.features["payments_expected"] == 4
        assert result.features["payments_made"] == 3

    def test_old_active_loan_missing_installments_is_delinquent(self) -> None:
        claim, tx = _paid_tx(1, date(2026, 1, 1))
        profile = BorrowerInput(
            borrower_id="B-OLD",
            evaluation_date=date(2026, 6, 15),
            informal_loans=[_base_loan(issue_date=date(2025, 6, 1))],
            repayment_claims=[claim],
            transactions=[tx],
        )
        result = assess(profile)
        assert result.status == "DELINQUENT"
        assert result.new_credit_blocked is True

    def test_explicit_overdue_is_delinquent(self) -> None:
        claim, tx = _paid_tx(1, date(2026, 1, 1))
        claim2, tx2 = _paid_tx(2, date(2026, 2, 1))
        profile = BorrowerInput(
            borrower_id="B-EXP",
            evaluation_date=date(2026, 4, 15),
            informal_loans=[_base_loan(declared_status="OVERDUE")],
            repayment_claims=[claim, claim2],
            transactions=[tx, tx2],
        )
        result = assess(profile)
        assert result.status == "DELINQUENT"

    def test_overdue_zero_repayment_is_severely_unpaid(self) -> None:
        result = assess(load_fixture("unpaid_loan.json"))
        assert result.status == "SEVERELY_UNPAID"
        assert result.new_credit_blocked is True
        assert result.hard_cap == 35

    def test_completed_loan_below_90_percent_is_delinquent(self) -> None:
        claim, tx = _paid_tx(1, date(2026, 1, 1))
        profile = BorrowerInput(
            borrower_id="B-UNDER",
            evaluation_date=date(2026, 7, 1),
            informal_loans=[_base_loan(declared_status="COMPLETED")],
            repayment_claims=[claim],
            transactions=[tx],
        )
        result = assess(profile)
        assert result.status == "DELINQUENT"
        assert (result.features["repayment_completion_ratio"] or 0) < 0.90

    def test_on_time_count_cannot_exceed_payment_count(self) -> None:
        result = assess(load_fixture("seasonal_business.json"))
        made = result.features["payments_made"]
        expected = result.features["payments_expected"]
        on_time_ratio = result.features["on_time_payment_ratio"]
        assert made <= expected
        assert on_time_ratio * expected <= made + 1e-9
