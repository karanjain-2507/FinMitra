"""
common/schemas.py

All shared Pydantic models used across the FinMitra Person 4 subsystem.

Design conventions:
  - Currency: INR, represented as float (positive numbers).
  - Ratios: 0.0–1.0 (income_volatility, confidence).
  - Scores: 0–100 or None.
  - Missing values: None — never substitute 0 for None.
  - Dates: YYYY-MM-DD strings (not used internally for calculations here).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class Reason(BaseModel):
    """A single explainability reason attached to any component result."""

    code: str = Field(
        description="Prefixed reason code, e.g. CP01, EV01, CF01, RP01."
    )
    direction: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"] = Field(
        description="Whether this reason helps, hurts, or is neutral."
    )
    impact: Optional[float] = Field(
        default=None,
        description="Approximate rupee or index impact; None when not quantifiable.",
    )
    message: str = Field(description="Human-readable explanation.")


class SafeEMI(BaseModel):
    """Affordable monthly instalment range produced by the Capacity Engine."""

    minimum: float = Field(ge=0, description="Lower bound of safe EMI in INR.")
    maximum: float = Field(ge=0, description="Upper bound of safe EMI in INR.")

    @model_validator(mode="after")
    def _min_le_max(self) -> "SafeEMI":
        if self.minimum > self.maximum:
            raise ValueError(
                f"SafeEMI minimum ({self.minimum}) must be ≤ maximum ({self.maximum})"
            )
        return self


# ---------------------------------------------------------------------------
# Capacity Engine schemas
# ---------------------------------------------------------------------------


class CapacityInput(BaseModel):
    """
    Primary input to the Capacity Engine.

    All monetary amounts are in INR (positive floats).
    income_volatility is a ratio in [0, 1].
    Loan-related fields are optional; when omitted the engine answers the
    generic question "what EMI can this borrower support?" instead of
    evaluating a specific loan request.
    """

    # --- Core income / expense ---
    conservative_monthly_inflow: float = Field(
        gt=0,
        description=(
            "Conservative estimate of monthly cash inflow in INR. "
            "Supplied by the cash-flow pipeline; treated as an authoritative input."
        ),
    )
    essential_household_expense: float = Field(
        ge=0,
        description="Monthly household essential expenditure in INR.",
    )
    essential_business_expense: float = Field(
        ge=0,
        description="Monthly business essential expenditure in INR.",
    )

    # --- Existing obligations ---
    existing_formal_emis: float = Field(
        ge=0,
        default=0.0,
        description=(
            "Monthly formal EMI obligations currently being paid (e.g. bank loans). "
            "0.0 means no formal EMIs; use None only when data is unavailable "
            "(Pydantic converts None to 0.0 here because formal EMIs default to zero "
            "when the borrower has no formal credit history — see notes)."
        ),
    )
    existing_informal_installments: float = Field(
        ge=0,
        default=0.0,
        description=(
            "Monthly informal installment obligations (e.g. supplier credit, "
            "chit funds). 0.0 means none known."
        ),
    )

    # --- Risk / volatility context ---
    income_volatility: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Coefficient of variation of monthly income as a ratio (0–1). "
            "Supplied by the cash-flow pipeline."
        ),
    )
    lowest_recent_monthly_inflow: float = Field(
        ge=0,
        description=(
            "Lowest observed monthly inflow over the recent statement window. "
            "Used in the seasonal stress test."
        ),
    )
    available_balance_buffer: float = Field(
        ge=0,
        description=(
            "Liquid buffer available at assessment time (e.g. average closing balance)."
        ),
    )

    # --- Delinquency context ---
    outstanding_delinquent_amount: float = Field(
        ge=0,
        default=0.0,
        description=(
            "Total outstanding overdue amount in INR. Surfaced in warnings and "
            "features. The Repayment Engine's new_credit_blocked flag takes "
            "precedence for the hard-block policy decision."
        ),
    )

    # --- Optional requested-loan fields ---
    requested_loan_amount: Optional[float] = Field(
        default=None,
        description="Principal of the loan being requested, in INR.",
    )
    annual_interest_rate: Optional[float] = Field(
        default=None,
        description=(
            "Annual interest rate as a decimal (e.g. 0.12 for 12%). "
            "Required when requested_loan_amount is supplied."
        ),
    )
    tenure_months: Optional[int] = Field(
        default=None,
        description=(
            "Loan tenure in months. Required when requested_loan_amount is supplied."
        ),
    )

    # --- Validators ---
    @field_validator("annual_interest_rate")
    @classmethod
    def _rate_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("annual_interest_rate must be >= 0")
        return v

    @field_validator("requested_loan_amount")
    @classmethod
    def _principal_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("requested_loan_amount must be > 0")
        return v

    @field_validator("tenure_months")
    @classmethod
    def _tenure_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("tenure_months must be > 0")
        return v

    @model_validator(mode="after")
    def _loan_fields_consistent(self) -> "CapacityInput":
        fields = (
            self.requested_loan_amount,
            self.annual_interest_rate,
            self.tenure_months,
        )
        provided = sum(f is not None for f in fields)
        if provided not in (0, 3):
            raise ValueError(
                "Provide all three loan fields (requested_loan_amount, "
                "annual_interest_rate, tenure_months) or none of them."
            )
        return self


class CapacityPolicy(BaseModel):
    """
    Policy configuration for the Capacity Engine.

    All values are configurable so that policy decisions are transparent and
    auditable. Defaults reflect the FinMitra design specification.
    """

    # Safe EMI as fraction of monthly surplus
    safe_emi_min_factor: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Lower bound factor applied to surplus to derive safe EMI min.",
    )
    safe_emi_max_factor: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Upper bound factor applied to surplus to derive safe EMI max.",
    )

    # Stress-test parameters
    income_stress_factor: float = Field(
        default=0.80,
        gt=0.0,
        le=1.0,
        description="Income multiplier for the 20%-drop stress test (0.80 = 20% drop).",
    )
    expense_stress_factor: float = Field(
        default=1.30,
        ge=1.0,
        description="Essential-expense multiplier for the 30%-increase stress test.",
    )
    zero_income_stress_enabled: bool = Field(
        default=True,
        description="Whether the zero-income-month stress test is enabled.",
    )

    # Max-principal tenures
    max_principal_tenures: List[int] = Field(
        default=[6, 12, 18],
        description="Tenures (months) for which max principal is calculated.",
    )

    # Annual interest rate used when the borrower has not specified a loan
    default_annual_interest_rate: float = Field(
        default=0.14,
        ge=0.0,
        description=(
            "Default annual interest rate (decimal) used for max-principal "
            "calculations when the borrower does not supply a specific rate."
        ),
    )

    # Thresholds that drive capacity status
    limited_capacity_threshold: float = Field(
        default=3000.0,
        ge=0.0,
        description=(
            "If safe_emi_max > 0 but < this value, status is LIMITED_CAPACITY "
            "rather than SUFFICIENT_CAPACITY."
        ),
    )

    @model_validator(mode="after")
    def _min_le_max_factor(self) -> "CapacityPolicy":
        if self.safe_emi_min_factor > self.safe_emi_max_factor:
            raise ValueError(
                "safe_emi_min_factor must be ≤ safe_emi_max_factor"
            )
        return self


class RequestedLoanAssessment(BaseModel):
    """Evaluation of a specific loan request against the borrower's safe EMI."""

    principal: float = Field(gt=0)
    annual_interest_rate: float = Field(ge=0)
    tenure_months: int = Field(gt=0)
    calculated_emi: float = Field(ge=0)

    within_safe_capacity: bool = Field(
        description="True when calculated_emi ≤ safe_emi_max."
    )
    emi_headroom: float = Field(
        description=(
            "safe_emi_max − calculated_emi. Positive means EMI fits "
            "comfortably; negative means it exceeds capacity."
        )
    )


class StressTestResult(BaseModel):
    """Output of a single stress test scenario."""

    name: str
    description: str

    baseline_monthly_surplus: float
    stressed_monthly_surplus: float

    baseline_safe_emi_max: float
    stressed_safe_emi_max: float

    passed: bool = Field(
        description=(
            "True when the stressed scenario still allows the borrower to "
            "service the safe EMI (stressed_safe_emi_max >= baseline_safe_emi_max * 0)."
            " Exact pass criterion is documented per test."
        )
    )
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Severity of the stress impact."
    )

    reasons: List[str] = Field(
        description="Deterministic, calculation-backed explanations."
    )


class CapacityResult(BaseModel):
    """
    Output of the Capacity Engine.

    score is always None — capacity produces rupee amounts, not a credit score.
    """

    component: str = Field(default="capacity")
    version: str = Field(default="1.0")

    score: Optional[float] = Field(
        default=None,
        description=(
            "Intentionally None. Capacity produces affordability amounts, "
            "not a creditworthiness score."
        ),
    )
    status: Literal[
        "SUFFICIENT_CAPACITY",
        "LIMITED_CAPACITY",
        "NO_CAPACITY",
        "BLOCKED",
        "INSUFFICIENT_DATA",
    ]
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Input-completeness-based confidence (0–1).",
    )

    features: Dict[str, Any] = Field(
        description="Key inputs and derived values for explainability."
    )

    safe_emi: SafeEMI
    max_principal: Dict[str, float] = Field(
        description=(
            "Maximum affordable principal keyed by tenure string, e.g. '6_months'."
        )
    )

    requested_loan: Optional[RequestedLoanAssessment] = Field(
        default=None,
        description="Assessment of the specific loan request, if provided.",
    )

    stress_tests: List[StressTestResult]

    reasons: List[Reason]
    warnings: List[str]

    @field_validator("score")
    @classmethod
    def _score_must_be_none(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            raise ValueError("Capacity score must always be None.")
        return None


# ---------------------------------------------------------------------------
# Upstream component result schemas
# (Contracts that the real Evidence / Cash-Flow / Repayment engines must satisfy.
# These are used directly by the Profile Assembler and by the mock engines.)
# ---------------------------------------------------------------------------


class EvidenceResult(BaseModel):
    """
    Public output contract for Person 1's Evidence Engine.

    The Profile Assembler consumes this schema. The real Evidence Engine
    must produce output that validates against this model.
    """

    component: str = Field(default="evidence")
    version: str

    score: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Evidence quality score (0–100) or None.",
    )
    confidence: float = Field(ge=0.0, le=1.0)

    evidence_grade: Literal["A", "B", "C", "D"] = Field(
        description=(
            "Grade D triggers a readiness-index ceiling of 75 in the "
            "Profile Assembler."
        )
    )
    insufficient_history: bool = Field(
        description=(
            "True when transaction history is too thin to draw conclusions. "
            "Sets readiness_index to None in the assembled profile."
        )
    )

    features: Dict[str, Any] = Field(default_factory=dict)
    reasons: List[Reason] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class CashflowResult(BaseModel):
    """
    Public output contract for Person 2's Cash-Flow Model.

    score contributes 55% to the readiness index.
    """

    component: str = Field(default="cashflow")
    version: str

    score: float = Field(
        ge=0,
        le=100,
        description="Cash-flow stability score (0–100). Required for readiness index.",
    )
    confidence: float = Field(ge=0.0, le=1.0)

    features: Dict[str, Any] = Field(default_factory=dict)
    reasons: List[Reason] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class RepaymentResult(BaseModel):
    """
    Public output contract for Person 3's Repayment Engine.

    score contributes 45% to the readiness index.
    new_credit_blocked triggers a hard block across the entire profile.
    """

    component: str = Field(default="repayment")
    version: str

    score: float = Field(
        ge=0,
        le=100,
        description="Repayment behaviour score (0–100). Required for readiness index.",
    )
    confidence: float = Field(ge=0.0, le=1.0)

    new_credit_blocked: bool = Field(
        description=(
            "Hard policy flag. When True, safe_emi is set to ₹0 and the "
            "readiness index is capped at 35."
        )
    )

    features: Dict[str, Any] = Field(default_factory=dict)
    reasons: List[Reason] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class FinMitraCreditEvidenceProfile(BaseModel):
    """
    Final assembled FinMitra Credit Evidence Profile.

    Produced by the Profile Assembler from the four component results.
    """

    profile_version: str = Field(default="1.0")

    borrower_id: Optional[str] = Field(default=None)

    # --- Readiness index (cash flow + repayment only) ---
    readiness_index: Optional[float] = Field(
        default=None,
        description=(
            "0.55 × cashflow_score + 0.45 × repayment_score, subject to "
            "policy ceilings. None when evidence indicates insufficient history."
        ),
    )
    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="min(evidence.confidence, cashflow.confidence, repayment.confidence, capacity.confidence).",
    )

    # --- Component results ---
    evidence: EvidenceResult
    cashflow: CashflowResult
    repayment: RepaymentResult
    capacity: CapacityResult

    # --- Safe EMI surfaced at profile level ---
    safe_emi: SafeEMI

    # --- Policy decisions and metadata ---
    policy_flags: List[str] = Field(
        description="Human-readable flags for policy decisions applied."
    )
    final_reasons: List[Reason] = Field(
        description="Consolidated reasons from all components."
    )
    final_warnings: List[str] = Field(
        description="Consolidated warnings from all components."
    )
