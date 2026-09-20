"""
Unit tests for FinMitra Person 1 Pydantic Schemas.
"""
from __future__ import annotations
import pytest
from datetime import date
from pydantic import ValidationError

from finmitra_person1.enums import (
    TransactionCategory,
    TransactionMode,
    DataSourceType,
    VerificationLevel,
    CategorySource,
    TransactionStatus,
    EvidenceGrade,
    EvidenceStatus,
    ConflictType,
    ConflictSeverity,
)
from finmitra_person1.schemas import (
    NormalizedTransaction,
    ProvenanceRecord,
    Reason,
    ConflictRecord,
    EvidenceResult,
    EvidenceBundle,
    BorrowerInput,
    SourceInput,
)


def test_normalized_transaction_valid():
    txn = NormalizedTransaction(
        transaction_id="TXN-001",
        date=date(2026, 8, 14),
        amount_paise=185000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.86,
        mode=TransactionMode.UPI,
        source=DataSourceType.BANK_STATEMENT,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        status=TransactionStatus.SUCCESS,
        model_eligible=True
    )
    assert txn.transaction_id == "TXN-001"
    assert txn.amount_paise == 185000
    assert txn.category_confidence == 0.86
    assert txn.model_eligible is True


def test_normalized_transaction_invalid_amount():
    with pytest.raises(ValidationError):
        NormalizedTransaction(
            transaction_id="TXN-002",
            date=date(2026, 8, 14),
            amount_paise=-500,  # Negative amount must fail
            direction="CREDIT",
            category=TransactionCategory.BUSINESS_INCOME,
            category_confidence=0.86,
            mode=TransactionMode.UPI,
            source=DataSourceType.BANK_STATEMENT,
            verification=VerificationLevel.SOURCE_CONNECTED,
            category_source=CategorySource.MERCHANT_QR_MATCH,
            model_eligible=True
        )


def test_normalized_transaction_invalid_confidence():
    with pytest.raises(ValidationError):
        NormalizedTransaction(
            transaction_id="TXN-003",
            date=date(2026, 8, 14),
            amount_paise=1000,
            direction="CREDIT",
            category=TransactionCategory.BUSINESS_INCOME,
            category_confidence=1.5,  # > 1.0 must fail
            mode=TransactionMode.UPI,
            source=DataSourceType.BANK_STATEMENT,
            verification=VerificationLevel.SOURCE_CONNECTED,
            category_source=CategorySource.MERCHANT_QR_MATCH,
            model_eligible=True
        )


def test_evidence_result_bounds():
    res = EvidenceResult(
        version="1.0.0",
        score=88.5,
        status="SUFFICIENT",
        confidence=0.92,
        evidence_grade="A",
        insufficient_history=False,
        features={"source_count": 3},
        reasons=[],
        warnings=[]
    )
    assert res.score == 88.5
    assert res.confidence == 0.92

    with pytest.raises(ValidationError):
        EvidenceResult(
            version="1.0.0",
            score=150.0,  # > 100 must fail
            status="SUFFICIENT",
            confidence=0.92,
            evidence_grade="A",
            insufficient_history=False
        )

    with pytest.raises(ValidationError):
        EvidenceResult(
            version="1.0.0",
            score=80.0,
            status="SUFFICIENT",
            confidence=85.0,  # > 1.0 must fail (should be 0.85)
            evidence_grade="B",
            insufficient_history=False
        )
