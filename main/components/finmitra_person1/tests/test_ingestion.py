"""
Unit tests for Ingestion adapters (JSON, CSV, Bank, UPI, POS, Ledger, Invoices, Cash).
"""
from __future__ import annotations
import json
import pytest

from finmitra_person1.enums import DataSourceType, TransactionMode
from finmitra_person1.ingestion import ingest_source, ingest_borrower, parse_borrower_payload
from finmitra_person1.ingestion.csv_adapter import CsvSourceAdapter
from finmitra_person1.ingestion.bank_statement import BankStatementAdapter
from finmitra_person1.schemas import BorrowerInput, SourceInput


def test_json_adapter_parses_records():
    payload = {
        "borrower_id": "TEST-01",
        "sources": [
            {
                "source_id": "SRC-01",
                "source_type": "UPI",
                "records": [
                    {"id": "U1", "date": "2026-05-01", "amount": 150.0, "narration": "UPI payment", "counterparty": "user@upi"}
                ]
            }
        ]
    }
    borrower = parse_borrower_payload(payload)
    assert borrower.borrower_id == "TEST-01"
    assert len(borrower.sources) == 1

    records = ingest_borrower(borrower)
    assert len(records) == 1
    assert records[0].source_record_id == "U1"
    assert records[0].raw_amount == 150.0


def test_csv_adapter_parses_tabular_data():
    csv_data = """Transaction ID,Date,Credit,Debit,Narration,Counterparty
TXN101,2026-03-01,1500.00,,UPI/Customer sale,rahul@upi
TXN102,2026-03-02,,800.00,NEFT/Vendor purchase,Wholesale Supplies
"""
    adapter = CsvSourceAdapter()
    records = adapter.parse(csv_data, source_id="CSV-SRC", source_type=DataSourceType.BANK_STATEMENT)
    assert len(records) == 2
    assert records[0].source_record_id == "TXN101"
    assert records[0].raw_direction == "CREDIT"
    assert records[0].raw_amount == "1500.00"
    assert records[1].source_record_id == "TXN102"
    assert records[1].raw_direction == "DEBIT"
    assert records[1].raw_amount == "800.00"


def test_bank_statement_heuristic_mode_detection():
    adapter = BankStatementAdapter()
    payload = [
        {"id": "B1", "date": "2026-01-01", "amount": 500, "narration": "UPI/123456/Customer Payment"},
        {"id": "B2", "date": "2026-01-02", "amount": 1000, "narration": "NEFT/VENDOR99/Supplier Bill"},
        {"id": "B3", "date": "2026-01-03", "amount": 2000, "narration": "POS SETTLEMENT EDC BATCH 12"},
        {"id": "B4", "date": "2026-01-04", "amount": 3000, "narration": "ATM CASH DEP AT BRANCH"}
    ]
    records = adapter.parse(payload, source_id="BNK-01", source_type=DataSourceType.BANK_STATEMENT)
    assert records[0].raw_mode == TransactionMode.UPI.value
    assert records[1].raw_mode == TransactionMode.BANK_TRANSFER.value
    assert records[2].raw_mode == TransactionMode.POS.value
    assert records[3].raw_mode == TransactionMode.CASH.value
