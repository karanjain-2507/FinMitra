"""
Pydantic Schemas for FinMitra Person 1 (Evidence Engine).
Defines the canonical data model, inputs, outputs, and validation rules.
"""
from __future__ import annotations
from datetime import date
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import (
    TransactionCategory,
    TransactionMode,
    DataSourceType,
    VerificationLevel,
    CategorySource,
    TransactionDirection,
    TransactionStatus,
    EvidenceGrade,
    EvidenceStatus,
    ReasonDirection,
    ConflictType,
    ConflictSeverity,
)


class ProvenanceRecord(BaseModel):
    """Traceability record linking a normalized transaction back to its raw origin."""
    source_type: DataSourceType
    source_id: str
    source_record_id: Optional[str] = None
    raw_data_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedTransaction(BaseModel):
    """
    Canonical, normalized financial transaction representation.
    Amounts are strictly stored in integer paise (1 INR = 100 paise).
    """
    transaction_id: str
    date: date
    amount_paise: int = Field(ge=0, description="Monetary amount in integer paise (non-negative)")
    direction: Literal["CREDIT", "DEBIT"]

    category: TransactionCategory
    category_confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")

    mode: TransactionMode

    source: DataSourceType
    source_record_id: Optional[str] = None

    verification: VerificationLevel
    category_source: CategorySource

    counterparty_id: Optional[str] = None
    counterparty_name: Optional[str] = None

    narration: Optional[str] = None

    status: TransactionStatus = TransactionStatus.SUCCESS

    duplicate_group_id: Optional[str] = None
    linked_transaction_ids: List[str] = Field(default_factory=list)

    model_eligible: bool
    anomaly_flag: bool = False
    anomaly_score: Optional[float] = None

    provenance: List[ProvenanceRecord] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("amount_paise")
    @classmethod
    def validate_amount_paise(cls, v: int) -> int:
        if v < 0:
            raise ValueError("amount_paise cannot be negative")
        return v

    @field_validator("category_confidence")
    @classmethod
    def validate_category_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"category_confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)


class SourceInput(BaseModel):
    """Individual data source bundle containing raw transaction records."""
    source_id: str
    source_type: DataSourceType
    records: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BorrowerInput(BaseModel):
    """Top-level borrower payload ingested into Person 1 subsystem."""
    borrower_id: str
    business_name: Optional[str] = None
    sources: List[SourceInput] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Reason(BaseModel):
    """Structured, explainable reason code explaining an evidence finding."""
    code: str = Field(description="Standardized code, e.g. EV01, EV04, EV11")
    direction: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]
    impact: Optional[float] = Field(default=None, description="Quantitative impact on score (optional)")
    message: str = Field(description="Human-understandable explanation of the reason")


class ConflictRecord(BaseModel):
    """Details of an observed contradiction across or within sources."""
    conflict_type: ConflictType
    severity: ConflictSeverity
    records: List[str] = Field(description="IDs or identifiers of conflicting records")
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class EvidenceResult(BaseModel):
    """
    Standardized component output consumed by downstream FinMitra engines.
    """
    component: Literal["evidence"] = "evidence"
    version: str

    score: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Evidence score on 0-100 scale")
    status: Literal["SUFFICIENT", "DEGRADED", "INSUFFICIENT"]

    confidence: float = Field(ge=0.0, le=1.0, description="Evidence confidence between 0.0 and 1.0")

    evidence_grade: Literal["A", "B", "C", "D"]
    insufficient_history: bool

    features: Dict[str, Any] = Field(default_factory=dict)

    reasons: List[Reason] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError(f"score must be between 0.0 and 100.0, got {v}")
        return round(v, 2) if v is not None else None


class EvidenceBundle(BaseModel):
    """Complete output bundle produced by Person 1."""
    borrower_id: str
    result: EvidenceResult
    normalized_transactions: List[NormalizedTransaction]
    source_summary: Dict[str, Any] = Field(default_factory=dict)
    conflicts: List[ConflictRecord] = Field(default_factory=list)
