"""
Unit tests for data normalization: amounts, dates, directions, modes.
"""
from __future__ import annotations
from datetime import date
import pytest

from finmitra_person1.enums import DataSourceType, TransactionMode
from finmitra_person1.ingestion.base import parse_amount_to_paise, parse_flexible_date, RawTransactionRecord
from finmitra_person1.normalization.normalize import normalize_record, normalize_direction, normalize_mode


def test_amount_parsing():
    assert parse_amount_to_paise(1850) == 185000
    assert parse_amount_to_paise(1850.50) == 185050
    assert parse_amount_to_paise("₹ 1,850.50") == 185050
    assert parse_amount_to_paise("1850") == 185000
    assert parse_amount_to_paise(None) is None
    assert parse_amount_to_paise("invalid") is None


def test_date_parsing():
    assert parse_flexible_date("2026-08-14") == date(2026, 8, 14)
    assert parse_flexible_date("14/08/2026") == date(2026, 8, 14)
    assert parse_flexible_date("14-08-2026") == date(2026, 8, 14)
    assert parse_flexible_date(date(2026, 8, 14)) == date(2026, 8, 14)
    assert parse_flexible_date("invalid-date") is None


def test_direction_normalization():
    assert normalize_direction("CR") == "CREDIT"
    assert normalize_direction("DEPOSIT") == "CREDIT"
    assert normalize_direction("DR") == "DEBIT"
    assert normalize_direction("WITHDRAWAL") == "DEBIT"
    assert normalize_direction(None) == "CREDIT"


def test_normalize_record_complete():
    raw_rec = RawTransactionRecord(
        source_type=DataSourceType.BANK_STATEMENT,
        source_id="BNK-1",
        source_record_id="REC-99",
        raw_date="2026-06-15",
        raw_amount="₹2,500.00",
        raw_direction="CR",
        raw_narration="POS Settlement batch 4",
        raw_counterparty="PineLabs",
        raw_mode="POS"
    )
    txn, err = normalize_record(raw_rec)
    assert err is None
    assert txn is not None
    assert txn.transaction_id == "REC-99"
    assert txn.amount_paise == 250000
    assert txn.date == date(2026, 6, 15)
    assert txn.direction == "CREDIT"
    assert txn.mode == TransactionMode.POS
