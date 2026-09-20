"""Stable input/output contracts for FinMitra engines.

All component packages (evidence, cash-flow, repayment, capacity) should
depend on these models. Do not import other persons' internals here.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


Direction = Literal["CREDIT", "DEBIT"]
InstallmentFrequency = Literal["MONTHLY", "WEEKLY", "BIWEEKLY"]
ReasonDirection = Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]
RepaymentStatus = Literal[
    "CURRENT",
    "BEHIND_SCHEDULE",
    "DELINQUENT",
    "SEVERELY_UNPAID",
    "COMPLETED",
    "INSUFFICIENT_EVIDENCE",
]


class ExtensibleModel(BaseModel):
    """Base model that accepts unknown fields so other engines can extend payloads."""

    model_config = ConfigDict(extra="allow")


class Transaction(ExtensibleModel):
    """A single cash movement. Amounts are always positive; use `direction` for sign."""

    transaction_id: str
    date: date
    amount: float
    direction: Direction
    category: Optional[str] = None
    counterparty_id: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    verified: Optional[bool] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: float) -> float:
        if value < 0:
            raise ValueError("amount must be >= 0; encode outflow with direction=DEBIT")
        return value


class Loan(ExtensibleModel):
    """Declared informal or formal obligation. Schedule fields may be incomplete."""

    loan_id: str
    lender_id: Optional[str] = None
    issue_date: date
    principal_amount: float
    installment_amount: Optional[float] = None
    installment_frequency: Optional[InstallmentFrequency] = None
    number_of_installments: Optional[int] = None
    first_due_date: Optional[date] = None
    declared_status: Optional[str] = None
    relationship_type: Optional[str] = None

    @field_validator("principal_amount")
    @classmethod
    def principal_must_be_positive(cls, value: float) -> float:
        if value < 0:
            raise ValueError("principal_amount must be >= 0")
        return value


class Repayment(ExtensibleModel):
    """A claimed or observed repayment against a loan.

    `transaction_id` is optional because some repayments are self-declared only.
    """

    repayment_id: str
    loan_id: str
    date: date
    amount: float
    transaction_id: Optional[str] = None
    source: Optional[str] = None
    verified: Optional[bool] = None
    confidence: Optional[float] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: float) -> float:
        if value < 0:
            raise ValueError("amount must be >= 0")
        return value


class StatementMetadata(ExtensibleModel):
    source: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    account_id: Optional[str] = None


class EvidenceInfo(ExtensibleModel):
    """Optional Person 1 evidence summary. Not coupled to Person 1 internals."""

    evidence_grade: Optional[str] = None
    verified_repayment_ratio: Optional[float] = None
    evidence_confidence: Optional[float] = None


class CashFlowInfo(ExtensibleModel):
    """Optional Person 2 cash-flow summary. Repayment status must not consume this."""

    cash_flow_score: Optional[float] = None
    cash_flow_confidence: Optional[float] = None


class BorrowerInput(ExtensibleModel):
    """Canonical borrower payload shared across engines."""

    borrower_id: str
    transactions: list[Transaction] = Field(default_factory=list)
    informal_loans: list[Loan] = Field(default_factory=list)
    repayment_claims: list[Repayment] = Field(default_factory=list)
    statement_metadata: Optional[StatementMetadata] = None
    evidence: Optional[EvidenceInfo] = None
    cash_flow: Optional[CashFlowInfo] = None
    evaluation_date: Optional[date] = None


class Reason(BaseModel):
    code: str
    direction: ReasonDirection
    impact: Optional[float] = None
    message: str


class ComponentResult(BaseModel):
    """Standardized engine output consumed by Person 4 (capacity + fusion)."""

    component: str
    version: str
    score: Optional[float] = None
    status: str
    confidence: float
    features: dict[str, Any] = Field(default_factory=dict)
    reasons: list[Reason] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    new_credit_blocked: bool = False
    hard_cap: Optional[float] = None
