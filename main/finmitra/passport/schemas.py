"""Typed contracts for selectively disclosed financial passports."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PassportClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_grade: Literal["A", "B", "C", "D", "INSUFFICIENT", "UNKNOWN"]
    cashflow_status: str
    repayment_status: str
    credit_status: Literal["ELIGIBLE_FOR_REVIEW", "BLOCKED", "INSUFFICIENT_DATA"]
    readiness_band: Literal["STRONG", "MODERATE", "DEVELOPING", "UNAVAILABLE"]
    confidence_band: Literal["HIGH", "MEDIUM", "LOW"]
    stress_checks_passed: int = Field(ge=0)
    stress_checks_total: int = Field(ge=0)


class PassportGoalClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_type: Literal["LOAN_READINESS", "SAVINGS_TARGET"]
    outcome: Literal[
        "ACHIEVABLE_NOW",
        "ACHIEVABLE_WITH_CHANGES",
        "BLOCKED",
        "INSUFFICIENT_DATA",
        "INVALID_GOAL",
    ]
    deadline_months: int = Field(ge=1, le=120)


class PassportProof(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["HMAC-SHA256"] = "HMAC-SHA256"
    key_id: str
    signature: str


class FinancialPassport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    credential_id: str
    issuer: Literal["FinMitra"] = "FinMitra"
    subject_id: str
    issued_at: str
    expires_at: str
    assessment_date: str
    claims: PassportClaims
    goal_claim: PassportGoalClaim | None = None
    proof: PassportProof


class PassportVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credential_id: str
    valid: bool
    status: Literal["VERIFIED", "EXPIRED", "INVALID", "NOT_FOUND"]
    verified_at: str
    issuer: str | None = None
    subject_id: str | None = None
    expires_at: str | None = None
    claims: PassportClaims | None = None
    goal_claim: PassportGoalClaim | None = None
