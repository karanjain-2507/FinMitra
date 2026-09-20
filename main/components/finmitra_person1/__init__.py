"""
FinMitra Person 1: Evidence Engine, Data Ingestion, and Normalization Subsystem.
"""
from __future__ import annotations

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
from .schemas import (
    NormalizedTransaction,
    ProvenanceRecord,
    SourceInput,
    BorrowerInput,
    Reason,
    ConflictRecord,
    EvidenceResult,
    EvidenceBundle,
)
from .evidence.engine import assess, build_evidence_bundle, EvidenceEngine

__version__ = "1.0.0"

__all__ = [
    "assess",
    "build_evidence_bundle",
    "EvidenceEngine",
    "NormalizedTransaction",
    "ProvenanceRecord",
    "SourceInput",
    "BorrowerInput",
    "Reason",
    "ConflictRecord",
    "EvidenceResult",
    "EvidenceBundle",
    "TransactionCategory",
    "TransactionMode",
    "DataSourceType",
    "VerificationLevel",
    "CategorySource",
    "TransactionDirection",
    "TransactionStatus",
    "EvidenceGrade",
    "EvidenceStatus",
    "ReasonDirection",
    "ConflictType",
    "ConflictSeverity",
]
