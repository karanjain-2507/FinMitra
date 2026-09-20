"""
Unit tests for data validation, future dates, zero values, and conflict detection.
"""
from __future__ import annotations
from datetime import date
import pytest

from finmitra_person1.enums import (
    TransactionCategory,
    TransactionMode,
    DataSourceType,
    VerificationLevel,
    CategorySource,
    ConflictType,
)
from finmitra_person1.schemas import NormalizedTransaction
from finmitra_person1.evidence.validation import validate_normalized_transactions
from finmitra_person1.normalization.deduplication import run_deduplication


def test_validation_future_date_quarantine():
    future_txn = NormalizedTransaction(
        transaction_id="TXN-FUT",
        date=date(2028, 1, 1),
        amount_paise=10000,
        direction="CREDIT",
        category=TransactionCategory.UNCLASSIFIED,
        category_confidence=0.25,
        mode=TransactionMode.UPI,
        source=DataSourceType.UPI,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.NONE,
        model_eligible=False
    )
    valid, errors, conflicts = validate_normalized_transactions([future_txn], reference_date=date(2026, 9, 1))
    assert len(valid) == 0
    assert len(errors) == 1
    assert "Future transaction date" in errors[0]["errors"][0]


def test_amount_mismatch_conflict_detection():
    # Two transactions sharing same reference with different amounts
    t1 = NormalizedTransaction(
        transaction_id="BANK-REC-1",
        date=date(2026, 6, 1),
        amount_paise=5000000,  # 50,000 INR
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.90,
        mode=TransactionMode.BANK_TRANSFER,
        source=DataSourceType.BANK_STATEMENT,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.INVOICE_MATCH,
        model_eligible=True,
        metadata={"reference": "INV-CONFLICT-REF"}
    )
    t2 = NormalizedTransaction(
        transaction_id="INV-REC-1",
        date=date(2026, 6, 1),
        amount_paise=500000,  # 5,000 INR
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.90,
        mode=TransactionMode.BANK_TRANSFER,
        source=DataSourceType.INVOICE,
        verification=VerificationLevel.DOCUMENT_MATCHED,
        category_source=CategorySource.INVOICE_MATCH,
        model_eligible=True,
        metadata={"reference": "INV-CONFLICT-REF"}
    )
    canonical, conflicts, stats = run_deduplication([t1, t2])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.AMOUNT_MISMATCH
