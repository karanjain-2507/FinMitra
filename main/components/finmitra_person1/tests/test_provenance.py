"""
Unit tests for Provenance preservation and merging.
"""
from __future__ import annotations
import pytest

from finmitra_person1.enums import DataSourceType
from finmitra_person1.schemas import ProvenanceRecord
from finmitra_person1.ingestion.base import RawTransactionRecord
from finmitra_person1.normalization.provenance import create_provenance, merge_provenances, compute_raw_hash


def test_create_provenance_from_raw():
    raw_rec = RawTransactionRecord(
        source_type=DataSourceType.BANK_STATEMENT,
        source_id="BANK-01",
        source_record_id="REC-100",
        raw_date="2026-06-01",
        raw_amount=5000.0,
        raw_direction="CREDIT",
        raw_narration="Customer payment"
    )
    prov = create_provenance(raw_rec)
    assert prov.source_type == DataSourceType.BANK_STATEMENT
    assert prov.source_id == "BANK-01"
    assert prov.source_record_id == "REC-100"
    assert prov.raw_data_hash is not None
    assert len(prov.raw_data_hash) == 16


def test_merge_provenances_deduplicates():
    p1 = ProvenanceRecord(source_type=DataSourceType.BANK_STATEMENT, source_id="B1", source_record_id="R1", raw_data_hash="abc")
    p2 = ProvenanceRecord(source_type=DataSourceType.UPI, source_id="U1", source_record_id="U1", raw_data_hash="xyz")
    p3 = ProvenanceRecord(source_type=DataSourceType.BANK_STATEMENT, source_id="B1", source_record_id="R1", raw_data_hash="abc")

    merged = merge_provenances([p1, p2], [p3])
    assert len(merged) == 2
    assert merged[0].source_id == "B1"
    assert merged[1].source_id == "U1"
