"""
Normalization and Categorization module for FinMitra Person 1.
"""
from __future__ import annotations

from .normalize import normalize_record, normalize_records
from .categorization import classify_transaction
from .deduplication import run_deduplication
from .provenance import create_provenance, merge_provenances
from .transfers import evaluate_transfer

__all__ = [
    "normalize_record",
    "normalize_records",
    "classify_transaction",
    "run_deduplication",
    "create_provenance",
    "merge_provenances",
    "evaluate_transfer",
]
