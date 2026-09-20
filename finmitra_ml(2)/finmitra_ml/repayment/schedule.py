"""Reconstruct expected installment schedules from declared loan terms."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Optional

from common.schemas import Loan
from repayment.models import ExpectedInstallment

FREQUENCY_DAYS = {
    "WEEKLY": 7,
    "BIWEEKLY": 14,
}


def add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def add_frequency(start: date, frequency: str, steps: int) -> date:
    if frequency == "MONTHLY":
        return add_months(start, steps)
    if frequency not in FREQUENCY_DAYS:
        raise ValueError(f"Unsupported installment_frequency: {frequency}")
    return start + timedelta(days=FREQUENCY_DAYS[frequency] * steps)


def schedule_anchor(loan: Loan) -> Optional[date]:
    if loan.first_due_date is not None:
        return loan.first_due_date
    if loan.issue_date is not None and loan.installment_frequency is not None:
        return add_frequency(loan.issue_date, loan.installment_frequency, 1)
    return None


def can_build_schedule(loan: Loan) -> bool:
    return bool(
        loan.installment_amount
        and loan.installment_amount > 0
        and loan.installment_frequency
        and loan.number_of_installments
        and loan.number_of_installments > 0
        and schedule_anchor(loan) is not None
    )


def build_full_schedule(loan: Loan) -> list[ExpectedInstallment]:
    if not can_build_schedule(loan):
        return []

    anchor = schedule_anchor(loan)
    assert anchor is not None
    assert loan.installment_amount is not None
    assert loan.installment_frequency is not None
    assert loan.number_of_installments is not None

    installments: list[ExpectedInstallment] = []
    for index in range(loan.number_of_installments):
        installments.append(
            ExpectedInstallment(
                loan_id=loan.loan_id,
                installment_index=index + 1,
                due_date=add_frequency(anchor, loan.installment_frequency, index),
                amount=float(loan.installment_amount),
            )
        )
    return installments


def expected_installments_as_of(
    loan: Loan, evaluation_date: date
) -> list[ExpectedInstallment]:
    """Installments with due_date on or before the evaluation date. Future dues are excluded."""

    return [
        installment
        for installment in build_full_schedule(loan)
        if installment.due_date <= evaluation_date
    ]


def expected_amount_as_of(loan: Loan, evaluation_date: date) -> Optional[float]:
    if not can_build_schedule(loan):
        return None
    return sum(item.amount for item in expected_installments_as_of(loan, evaluation_date))


def days_past_due(
    due_date: date,
    evaluation_date: date,
    *,
    covered: bool = False,
    paid_date: Optional[date] = None,
) -> int:
    """Days past due, never negative. Future unpaid installments contribute 0."""

    if covered:
        if paid_date is None:
            return 0
        return max(0, (paid_date - due_date).days)
    return max(0, (evaluation_date - due_date).days)
