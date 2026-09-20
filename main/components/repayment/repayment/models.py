"""Repayment-internal models. These are not the Person 4 fusion contract."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ExpectedInstallment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loan_id: str
    installment_index: int
    due_date: date
    amount: float


class PaymentMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repayment_id: str
    loan_id: str
    transaction_id: Optional[str] = None
    payment_date: Optional[date] = None
    matched_amount: float
    match_confidence: float
    match_method: str
    verified: bool = False
    contradictory: bool = False


class InstallmentAllocation(BaseModel):
    loan_id: str
    installment_index: int
    due_date: date
    expected_amount: float
    paid_amount: float
    paid_date: Optional[date] = None
    on_time: bool = False
    digitally_matched: bool = False
