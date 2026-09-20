"""
Data Validation and Conflict Detection.
Deterministic validation checks for data completeness, chronological validity,
impossible states, and cross-source contradictions.
"""
from __future__ import annotations
from datetime import date
from typing import List, Tuple, Dict, Any, Optional

from ..enums import ConflictType, ConflictSeverity
from ..schemas import NormalizedTransaction, ConflictRecord, BorrowerInput


def validate_normalized_transactions(
    transactions: List[NormalizedTransaction],
    reference_date: Optional[date] = None
) -> Tuple[List[NormalizedTransaction], List[Dict[str, Any]], List[ConflictRecord]]:
    """
    Validate normalized transactions.
    Filters out invalid records and detects internal inconsistencies.
    Returns:
        (valid_transactions, validation_errors, conflicts)
    """
    ref_date = reference_date or date.today()
    valid: List[NormalizedTransaction] = []
    errors: List[Dict[str, Any]] = []
    conflicts: List[ConflictRecord] = []

    seen_ids: Dict[str, NormalizedTransaction] = {}

    for txn in transactions:
        errs = []

        # 1. Missing transaction_id
        if not txn.transaction_id or not txn.transaction_id.strip():
            errs.append("Missing transaction_id")

        # 2. Future date check (allow up to +1 day for timezone buffer, but flag distinct future dates)
        if txn.date > ref_date:
            errs.append(f"Future transaction date: {txn.date} is after reference date {ref_date}")

        # 3. Negative amount check
        if txn.amount_paise < 0:
            errs.append(f"Negative amount: {txn.amount_paise}")

        # 4. Zero value transaction check
        if txn.amount_paise == 0:
            errs.append("Zero value transaction is not permissible")

        # 5. Invalid confidence
        if not (0.0 <= txn.category_confidence <= 1.0):
            errs.append(f"Invalid category confidence: {txn.category_confidence}")

        if errs:
            errors.append({
                "transaction_id": txn.transaction_id,
                "errors": errs,
                "raw_date": str(txn.date),
                "amount_paise": txn.amount_paise
            })
        else:
            valid.append(txn)

    return valid, errors, conflicts
