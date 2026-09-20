"""Canonical input contract for the integrated four-person pipeline."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CapacityContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    essential_household_expense: float = Field(ge=0)
    available_balance_buffer: float = Field(default=0, ge=0)
    existing_formal_emis: float = Field(default=0, ge=0)
    existing_informal_installments: float | None = Field(default=None, ge=0)
    essential_business_expense: float | None = Field(default=None, ge=0)
    outstanding_delinquent_amount: float | None = Field(default=None, ge=0)
    requested_loan_amount: float | None = Field(default=None, gt=0)
    annual_interest_rate: float | None = Field(default=None, ge=0)
    tenure_months: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def complete_requested_loan(self) -> "CapacityContext":
        fields = (
            self.requested_loan_amount,
            self.annual_interest_rate,
            self.tenure_months,
        )
        if sum(value is not None for value in fields) not in (0, 3):
            raise ValueError(
                "requested_loan_amount, annual_interest_rate, and tenure_months "
                "must be supplied together"
            )
        return self


class IntegratedBorrowerInput(BaseModel):
    """One input that feeds all four team components."""

    model_config = ConfigDict(extra="forbid")

    borrower_id: str = Field(min_length=1)
    business_name: str | None = None
    evaluation_date: date
    sources: list[dict[str, Any]] = Field(min_length=1)
    informal_loans: list[dict[str, Any]] = Field(default_factory=list)
    repayment_claims: list[dict[str, Any]] = Field(default_factory=list)
    capacity_context: CapacityContext
    metadata: dict[str, Any] = Field(default_factory=dict)
