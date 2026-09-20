"""
Unit tests for deterministic transaction categorization rules.
"""
from __future__ import annotations
import pytest

from finmitra_person1.enums import (
    TransactionCategory,
    CategorySource,
    VerificationLevel,
    DataSourceType,
)
from finmitra_person1.ingestion.base import RawTransactionRecord
from finmitra_person1.normalization.categorization import classify_transaction


def test_merchant_qr_categorization():
    rec = RawTransactionRecord(
        source_type=DataSourceType.QR,
        source_id="QR-01",
        source_record_id="Q1",
        raw_date="2026-05-01",
        raw_amount=500.0,
        raw_narration="Payment for groceries",
        raw_counterparty="user@okaxis",
        metadata={"is_merchant_qr": True}
    )
    cat, conf, src, ver, model_elig = classify_transaction(rec, "CREDIT", 50000)
    assert cat == TransactionCategory.BUSINESS_INCOME
    assert conf >= 0.90
    assert src == CategorySource.MERCHANT_QR_MATCH
    assert ver == VerificationLevel.MERCHANT_MATCHED
    assert model_elig is True


def test_self_declared_cash_income_is_not_model_eligible():
    rec = RawTransactionRecord(
        source_type=DataSourceType.SELF_DECLARATION,
        source_id="DECL-01",
        source_record_id="D1",
        raw_date="2026-05-01",
        raw_amount=80000.0,
        raw_narration="Self declared monthly cash sales",
        metadata={"is_self_declared": True}
    )
    cat, conf, src, ver, model_elig = classify_transaction(rec, "CREDIT", 8000000)
    assert cat == TransactionCategory.SELF_DECLARED_CASH_INCOME
    assert src == CategorySource.SELF_DECLARED
    assert ver == VerificationLevel.SELF_DECLARED
    assert model_elig is False  # CRITICAL: Must be excluded from predictive modeling


def test_internal_transfer_categorization():
    rec = RawTransactionRecord(
        source_type=DataSourceType.BANK_STATEMENT,
        source_id="BNK-01",
        source_record_id="B1",
        raw_date="2026-05-01",
        raw_amount=40000.0,
        raw_narration="Self transfer from savings to current account",
        raw_counterparty="Self Savings"
    )
    cat, conf, src, ver, model_elig = classify_transaction(rec, "CREDIT", 4000000)
    assert cat == TransactionCategory.TRANSFER
    assert src == CategorySource.NARRATION_RULE
    assert model_elig is False


def test_uncorroborated_cash_deposit():
    rec = RawTransactionRecord(
        source_type=DataSourceType.BANK_STATEMENT,
        source_id="BNK-01",
        source_record_id="B2",
        raw_date="2026-05-01",
        raw_amount=30000.0,
        raw_narration="Cash deposit at branch counter",
        raw_mode="CASH"
    )
    cat, conf, src, ver, model_elig = classify_transaction(rec, "CREDIT", 3000000)
    assert cat == TransactionCategory.CASH_DEPOSIT
    assert model_elig is False  # Cash deposit is not automatically verified revenue


def test_ambiguous_credit_remains_unclassified():
    rec = RawTransactionRecord(
        source_type=DataSourceType.BANK_STATEMENT,
        source_id="BNK-01",
        source_record_id="B3",
        raw_date="2026-05-01",
        raw_amount=2000.0,
        raw_narration="UPI/P2P/random transfer from friend",
        raw_counterparty="friend@upi"
    )
    cat, conf, src, ver, model_elig = classify_transaction(rec, "CREDIT", 200000)
    assert cat == TransactionCategory.UNCLASSIFIED
    assert conf <= 0.40
    assert src == CategorySource.NONE
    assert model_elig is False
