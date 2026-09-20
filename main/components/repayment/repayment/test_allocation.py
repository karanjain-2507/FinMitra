"""DPD floor and oldest-due-first installment allocation."""

from __future__ import annotations

from datetime import date

from common.schemas import Loan
from repayment.features import (
    COMPLETED_LOAN_REPAYMENT_RATIO,
    INSTALLMENT_COVERAGE_RATIO,
    allocate_installments,
    installment_is_covered,
)
from repayment.matching import EXPLICIT_LOAN_ID
from repayment.models import PaymentMatch
from repayment.schedule import days_past_due


def _loan() -> Loan:
    return Loan(
        loan_id="L-ALLOC",
        lender_id="L1",
        issue_date=date(2025, 12, 1),
        principal_amount=10000,
        installment_amount=5000,
        installment_frequency="MONTHLY",
        number_of_installments=2,
        first_due_date=date(2026, 1, 1),
    )


def _match(repayment_id: str, amount: float, day: date) -> PaymentMatch:
    return PaymentMatch(
        repayment_id=repayment_id,
        loan_id="L-ALLOC",
        transaction_id=f"T-{repayment_id}",
        payment_date=day,
        matched_amount=amount,
        match_confidence=0.9,
        match_method=EXPLICIT_LOAN_ID,
        verified=True,
    )


class TestAllocationAndDpd:
    def test_partial_payment(self) -> None:
        allocations = allocate_installments(
            _loan(),
            [_match("R1", 3000, date(2026, 1, 2))],
            date(2026, 2, 15),
        )
        assert allocations[0].paid_amount == 3000
        assert not installment_is_covered(allocations[0].paid_amount, 5000)
        assert allocations[1].paid_amount == 0

    def test_multiple_partial_payments_oldest_due_first(self) -> None:
        allocations = allocate_installments(
            _loan(),
            [
                _match("R1", 3000, date(2026, 1, 3)),
                _match("R2", 3000, date(2026, 1, 10)),
                _match("R3", 4000, date(2026, 2, 2)),
            ],
            date(2026, 2, 15),
        )
        assert allocations[0].paid_amount == 5000
        assert allocations[1].paid_amount == 5000
        assert installment_is_covered(allocations[0].paid_amount, 5000)
        assert installment_is_covered(allocations[1].paid_amount, 5000)

    def test_exact_payment(self) -> None:
        allocations = allocate_installments(
            _loan(),
            [_match("R1", 5000, date(2026, 1, 1))],
            date(2026, 1, 15),
        )
        assert allocations[0].paid_amount == 5000
        assert allocations[0].on_time is True

    def test_ninety_five_percent_threshold(self) -> None:
        assert INSTALLMENT_COVERAGE_RATIO == 0.95
        assert COMPLETED_LOAN_REPAYMENT_RATIO == 0.90
        assert installment_is_covered(4750, 5000) is True

    def test_below_ninety_five_percent(self) -> None:
        assert installment_is_covered(4749, 5000) is False

    def test_future_installment_dpd_is_not_negative(self) -> None:
        dpd = days_past_due(date(2026, 6, 1), date(2026, 4, 15), covered=False)
        assert dpd >= 0
        assert dpd == 0
        allocations = allocate_installments(_loan(), [], date(2025, 12, 15))
        assert allocations == []
        assert days_past_due(date(2026, 1, 1), date(2025, 12, 15)) == 0
