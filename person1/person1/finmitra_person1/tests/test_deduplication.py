"""
Unit tests for 3-level deduplication and cross-source matching.
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
from finmitra_person1.schemas import NormalizedTransaction, ProvenanceRecord
from finmitra_person1.normalization.deduplication import run_deduplication


def test_level1_exact_id_deduplication():
    t1 = NormalizedTransaction(
        transaction_id="TXN-DUP-1",
        date=date(2026, 5, 1),
        amount_paise=100000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.90,
        mode=TransactionMode.UPI,
        source=DataSourceType.UPI,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        model_eligible=True,
        provenance=[ProvenanceRecord(source_type=DataSourceType.UPI, source_id="SRC-1", source_record_id="TXN-DUP-1")]
    )
    t2 = NormalizedTransaction(
        transaction_id="TXN-DUP-1",  # Same ID
        date=date(2026, 5, 1),
        amount_paise=100000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.90,
        mode=TransactionMode.UPI,
        source=DataSourceType.UPI,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        model_eligible=True,
        provenance=[ProvenanceRecord(source_type=DataSourceType.UPI, source_id="SRC-1", source_record_id="TXN-DUP-1")]
    )
    canonical, conflicts, stats = run_deduplication([t1, t2])
    assert len(canonical) == 1
    assert stats["exact_duplicates"] == 1
    assert canonical[0].duplicate_group_id is not None
    assert len(canonical[0].linked_transaction_ids) == 1


def test_level3_cross_source_deduplication():
    bank_rec = NormalizedTransaction(
        transaction_id="BNK-SETTLE-01",
        date=date(2026, 5, 10),
        amount_paise=185000,
        direction="CREDIT",
        category=TransactionCategory.UNCLASSIFIED,
        category_confidence=0.25,
        mode=TransactionMode.UPI,
        source=DataSourceType.BANK_STATEMENT,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.NONE,
        model_eligible=False,
        metadata={"reference": "UPI-REF-777"},
        provenance=[ProvenanceRecord(source_type=DataSourceType.BANK_STATEMENT, source_id="BNK-1", source_record_id="BNK-SETTLE-01")]
    )
    upi_rec = NormalizedTransaction(
        transaction_id="UPI-PAY-01",
        date=date(2026, 5, 10),
        amount_paise=185000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.95,
        mode=TransactionMode.UPI,
        source=DataSourceType.QR,
        verification=VerificationLevel.MERCHANT_MATCHED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        model_eligible=True,
        metadata={"reference": "UPI-REF-777"},
        provenance=[ProvenanceRecord(source_type=DataSourceType.QR, source_id="QR-1", source_record_id="UPI-PAY-01")]
    )
    canonical, conflicts, stats = run_deduplication([bank_rec, upi_rec])
    assert len(canonical) == 1
    assert stats["cross_source_matches"] == 1
    assert canonical[0].verification in (VerificationLevel.CROSS_SOURCE_CORROBORATED, VerificationLevel.MERCHANT_MATCHED)
    # Check provenance preserves BOTH bank and QR sources!
    assert len(canonical[0].provenance) == 2


def test_no_false_dedup_of_different_dates():
    t1 = NormalizedTransaction(
        transaction_id="TXN-DAY-1",
        date=date(2026, 5, 1),
        amount_paise=100000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.90,
        mode=TransactionMode.UPI,
        source=DataSourceType.UPI,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        model_eligible=True
    )
    t2 = NormalizedTransaction(
        transaction_id="TXN-DAY-2",
        date=date(2026, 5, 15),  # 14 days later
        amount_paise=100000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.90,
        mode=TransactionMode.UPI,
        source=DataSourceType.UPI,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        model_eligible=True
    )
    canonical, conflicts, stats = run_deduplication([t1, t2])
    assert len(canonical) == 2
    assert stats["exact_duplicates"] == 0
