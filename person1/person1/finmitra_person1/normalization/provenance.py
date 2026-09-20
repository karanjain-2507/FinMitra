"""
Provenance Tracking and Builder.
Preserves full origin traceability from raw source records to normalized transactions.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import hashlib
import json

from ..enums import DataSourceType
from ..schemas import ProvenanceRecord
from ..ingestion.base import RawTransactionRecord


def compute_raw_hash(raw_rec: RawTransactionRecord) -> str:
    """Compute deterministic SHA-256 hash of raw record content."""
    content = {
        "source_type": raw_rec.source_type.value,
        "source_id": raw_rec.source_id,
        "source_record_id": raw_rec.source_record_id,
        "raw_date": str(raw_rec.raw_date),
        "raw_amount": str(raw_rec.raw_amount),
        "raw_direction": raw_rec.raw_direction,
        "raw_narration": raw_rec.raw_narration,
        "raw_counterparty": raw_rec.raw_counterparty,
        "raw_reference": raw_rec.raw_reference,
    }
    dumped = json.dumps(content, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:16]


def create_provenance(raw_rec: RawTransactionRecord) -> ProvenanceRecord:
    """Create a single ProvenanceRecord from a RawTransactionRecord."""
    return ProvenanceRecord(
        source_type=raw_rec.source_type,
        source_id=raw_rec.source_id,
        source_record_id=raw_rec.source_record_id,
        raw_data_hash=compute_raw_hash(raw_rec),
        metadata=raw_rec.metadata.copy() if raw_rec.metadata else {}
    )


def merge_provenances(list_a: List[ProvenanceRecord], list_b: List[ProvenanceRecord]) -> List[ProvenanceRecord]:
    """Merge two provenance lists without duplicating source records."""
    seen = set()
    merged: List[ProvenanceRecord] = []
    for prov in list_a + list_b:
        key = (prov.source_type, prov.source_id, prov.source_record_id, prov.raw_data_hash)
        if key not in seen:
            seen.add(key)
            merged.append(prov)
    return merged
