"""Typed, language-neutral contracts for What If planning."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


Money = Annotated[Decimal, Field(allow_inf_nan=False)]
GoalMoney = Annotated[
    Decimal,
    Field(gt=0, le=Decimal("100000000.00"), max_digits=11, decimal_places=2, allow_inf_nan=False),
]
NonNegativeGoalMoney = Annotated[
    Decimal,
    Field(ge=0, le=Decimal("100000000.00"), max_digits=11, decimal_places=2, allow_inf_nan=False),
]


class LoanReadinessGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["LOAN_READINESS"]
    title: str = Field(min_length=1, max_length=80)
    target_amount: GoalMoney
    deadline_months: int = Field(ge=1, le=120)
    annual_interest_rate: Decimal = Field(
        ge=0, le=1, max_digits=7, decimal_places=6, allow_inf_nan=False
    )
    tenure_months: int = Field(ge=1, le=360)
    desired_buffer: NonNegativeGoalMoney | None = None


class SavingsTargetGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["SAVINGS_TARGET"]
    title: str = Field(min_length=1, max_length=80)
    target_amount: GoalMoney
    current_goal_savings: NonNegativeGoalMoney = Decimal("0")
    deadline_months: int = Field(ge=1, le=120)
    conservative_contribution_factor: Decimal | None = Field(
        default=None, gt=0, le=1, allow_inf_nan=False
    )


Goal = Annotated[
    Union[LoanReadinessGoal, SavingsTargetGoal],
    Field(discriminator="type"),
]

Outcome = Literal[
    "ACHIEVABLE_NOW",
    "ACHIEVABLE_WITH_CHANGES",
    "BLOCKED",
    "INSUFFICIENT_DATA",
    "INVALID_GOAL",
]


class StressTestSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    severity: str
    stressed_monthly_surplus: Money | None = None


class FinancialBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    borrower_id: str | None = None
    evaluation_date: date
    conservative_monthly_inflow: Money = Field(ge=0)
    household_expense: Money = Field(ge=0)
    business_expense: Money = Field(ge=0)
    formal_emis: Money = Field(ge=0)
    informal_installments: Money = Field(ge=0)
    monthly_surplus: Money
    available_balance_buffer: Money = Field(ge=0)
    safe_emi_min: Money = Field(ge=0)
    safe_emi_max: Money = Field(ge=0)
    safe_emi_max_factor: Decimal = Field(gt=0, le=1, allow_inf_nan=False)
    new_credit_blocked: bool
    repayment_status: str
    insufficient_history: bool
    cashflow_status: str
    overall_confidence: Decimal = Field(ge=0, le=1, allow_inf_nan=False)
    stress_tests: list[StressTestSummary] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_capacity(self) -> "FinancialBaseline":
        if self.safe_emi_min > self.safe_emi_max:
            raise ValueError("safe_emi_min must not exceed safe_emi_max")
        if self.new_credit_blocked and self.safe_emi_max != 0:
            raise ValueError("blocked assessments must have zero safe EMI")
        return self


class GoalSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["LOAN_READINESS", "SAVINGS_TARGET"]
    title: str
    target_amount: Money
    deadline_months: int
    annual_interest_rate: Decimal | None = None
    tenure_months: int | None = None
    current_goal_savings: Money | None = None
    desired_buffer: Money | None = None


class CurrentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_inflow: Money | None
    monthly_expenses: Money
    existing_monthly_obligations: Money
    monthly_surplus: Money | None
    safe_emi_min: Money | None
    safe_emi_max: Money | None
    available_balance_buffer: Money
    overall_confidence: Decimal


class RequiredState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_emi: Money | None = None
    required_monthly_saving: Money | None = None
    required_monthly_surplus: Money | None = None
    desired_buffer: Money | None = None
    projected_goal_amount: Money | None = None


class FinancialGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emi_gap: Money | None = Decimal("0")
    monthly_cashflow_gap: Money | None = Decimal("0")
    monthly_savings_gap: Money | None = Decimal("0")
    buffer_gap: Money | None = Decimal("0")
    monthly_buffer_contribution: Money | None = Decimal("0")


class PlanPath(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "REDUCE_EXPENSES",
        "INCREASE_INCOME",
        "MIXED_CHANGE",
        "LOWER_PRINCIPAL",
        "EXTEND_LOAN_TENURE",
        "EXTEND_SAVINGS_DEADLINE",
        "REDUCE_TARGET",
        "BUILD_BUFFER",
        "RESOLVE_REPAYMENT_BLOCK",
    ]
    message_key: str
    available: bool = True
    monthly_amount: Money | None = None
    expense_reduction: Money | None = None
    income_increase: Money | None = None
    new_principal: Money | None = None
    new_tenure_months: int | None = None
    new_deadline_months: int | None = None
    new_target_amount: Money | None = None


class SafetySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_credit_blocked: bool
    insufficient_history: bool
    repayment_status: str
    failed_stress_tests: list[str]
    warning_keys: list[str]
    missing_fields: list[str] = Field(default_factory=list)


class PlanAssumption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    params: dict[str, Any] = Field(default_factory=dict)


class WhatIfResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal["1.0"] = "1.0"
    outcome: Outcome
    goal: GoalSnapshot
    current_state: CurrentState
    required_state: RequiredState
    gap: FinancialGap
    paths: list[PlanPath]
    safety: SafetySummary
    assumptions: list[PlanAssumption]
    message_keys: list[str]


class ShareableGoal(BaseModel):
    """Explicit allowlist for user-approved What If sharing."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["LOAN_READINESS", "SAVINGS_TARGET"]
    title: str | None = None
    target_amount: Money
    deadline_months: int
    annual_interest_rate: Decimal | None = None
    tenure_months: int | None = None


class ShareableWhatIfSummary(BaseModel):
    """Privacy-safe projection summary; never include the user's baseline."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    outcome: Outcome
    goal: ShareableGoal
    required_emi: Money | None = None
    required_monthly_saving: Money | None = None
    monthly_gap: Money | None = None
    new_credit_blocked: bool
