"""
Multi-Level Deduplication and Economic Event Consolidation.
Detects:
1. Exact ID duplicates
2. Strong fingerprint duplicates
3. Cross-source payment and settlement matches
Preserves complete provenance without deleting source trail.
"""
from __future__ import annotations
from typing import List, Dict, Set, Tuple, Optional
from datetime import timedelta
import hashlib
import uuid

from ..enums import (
    DataSourceType,
    VerificationLevel,
    CategorySource,
    TransactionCategory,
    TransactionDirection,
    TransactionMode,
)
from ..schemas import NormalizedTransaction, ConflictRecord
from ..enums import ConflictType, ConflictSeverity
from ..config import CROSS_SOURCE_WINDOW_DAYS, DEDUP_AMOUNT_TOLERANCE_PCT
from .provenance import merge_provenances


def compute_fingerprint(txn: NormalizedTransaction) -> str:
    """Compute strong fingerprint for within-source duplicate detection."""
    cp = (txn.counterparty_id or txn.counterparty_name or "").strip().lower()
    narr = (txn.narration or "").strip().lower()[:30]
    return f"{txn.date}_{txn.amount_paise}_{txn.direction}_{txn.mode}_{cp}_{narr}"


def run_deduplication(
    transactions: List[NormalizedTransaction]
) -> Tuple[List[NormalizedTransaction], List[ConflictRecord], Dict[str, Any]]:
    """
    Run 3-level deduplication and cross-source matching.
    Returns:
        (deduplicated_canonical_transactions, conflicts, dedup_stats)
    """
    if not transactions:
        return [], [], {"total_raw": 0, "canonical_count": 0, "duplicate_count": 0, "cross_source_matches": 0}

    conflicts: List[ConflictRecord] = []
    seen_ids: Dict[str, NormalizedTransaction] = {}
    fingerprint_map: Dict[str, List[NormalizedTransaction]] = {}
    
    # Track stats
    exact_duplicates = 0
    fingerprint_duplicates = 0
    cross_source_matches = 0

    # Step 1: Level 1 (Exact ID) & Level 2 (Fingerprint within same source)
    level1_filtered: List[NormalizedTransaction] = []

    for txn in transactions:
        if txn.transaction_id in seen_ids:
            # Level 1 duplicate
            exact_duplicates += 1
            existing = seen_ids[txn.transaction_id]
            group_hash = hashlib.md5(f"{existing.transaction_id}_{txn.transaction_id}".encode("utf-8")).hexdigest()[:8].upper()
            group_id = existing.duplicate_group_id or f"DG-{group_hash}"
            existing.duplicate_group_id = group_id
            existing.linked_transaction_ids.append(txn.transaction_id)
            existing.provenance = merge_provenances(existing.provenance, txn.provenance)

            # Check if amount or date conflicts with existing record
            if existing.amount_paise != txn.amount_paise:
                conflicts.append(
                    ConflictRecord(
                        conflict_type=ConflictType.AMOUNT_MISMATCH,
                        severity=ConflictSeverity.HIGH,
                        records=[existing.transaction_id, txn.transaction_id],
                        message=f"Duplicate transaction ID {txn.transaction_id} has conflicting amounts: {existing.amount_paise} paise vs {txn.amount_paise} paise.",
                        details={"existing_amount": existing.amount_paise, "new_amount": txn.amount_paise}
                    )
                )
            continue

        seen_ids[txn.transaction_id] = txn

        # Fingerprint check within same source
        fp = f"{txn.source.value}_{compute_fingerprint(txn)}"
        if fp in fingerprint_map:
            fingerprint_duplicates += 1
            existing = fingerprint_map[fp][0]
            group_hash = hashlib.md5(f"{existing.transaction_id}_{txn.transaction_id}".encode("utf-8")).hexdigest()[:8].upper()
            group_id = existing.duplicate_group_id or f"DG-{group_hash}"
            existing.duplicate_group_id = group_id
            existing.linked_transaction_ids.append(txn.transaction_id)
            existing.provenance = merge_provenances(existing.provenance, txn.provenance)
            continue

        fingerprint_map[fp] = [txn]
        level1_filtered.append(txn)

    # Step 2: Level 3 (Cross-Source Settlement and Corroboration Matching)
    # Match records across different sources that represent the same underlying economic event
    # e.g., Bank Credit <-> UPI Credit, Bank Debit <-> Supplier Invoice, POS Settlement <-> Bank Statement
    used_in_cross_source: Set[str] = set()
    canonical_list: List[NormalizedTransaction] = []

    # Sort chronologically for deterministic matching
    sorted_txns = sorted(level1_filtered, key=lambda t: (t.date, t.amount_paise, t.transaction_id))

    for i, txn_a in enumerate(sorted_txns):
        if txn_a.transaction_id in used_in_cross_source:
            continue

        for j in range(i + 1, len(sorted_txns)):
            txn_b = sorted_txns[j]
            if txn_b.transaction_id in used_in_cross_source:
                continue

            # Check date window
            days_diff = abs((txn_b.date - txn_a.date).days)
            if days_diff > CROSS_SOURCE_WINDOW_DAYS:
                continue

            # Must be different data sources
            if txn_a.source == txn_b.source:
                continue

            # Must share direction (both incoming revenue or both outgoing expense)
            # Or settlement pair (e.g. UPI collection & Bank credit)
            if txn_a.direction != txn_b.direction:
                continue

            # Amount match check (exact or within small percentage tolerance for MDR/gateway fees)
            amt_a = txn_a.amount_paise
            amt_b = txn_b.amount_paise
            diff_pct = abs(amt_a - amt_b) / max(amt_a, amt_b, 1)

            # Check reference match (UTR, invoice ID, etc.)
            ref_a = txn_a.metadata.get("reference") or txn_a.metadata.get("utr") or txn_a.source_record_id
            ref_b = txn_b.metadata.get("reference") or txn_b.metadata.get("utr") or txn_b.source_record_id
            has_ref_match = (
                bool(ref_a and ref_b and str(ref_a).strip().lower() == str(ref_b).strip().lower())
            )

            is_match = False
            if has_ref_match:
                if amt_a == amt_b or diff_pct <= DEDUP_AMOUNT_TOLERANCE_PCT:
                    is_match = True
                else:
                    # Material conflict between records claiming same reference ID!
                    conflicts.append(
                        ConflictRecord(
                            conflict_type=ConflictType.AMOUNT_MISMATCH,
                            severity=ConflictSeverity.HIGH,
                            records=[txn_a.transaction_id, txn_b.transaction_id],
                            message=f"Cross-source reference match '{ref_a}' has conflicting amounts: {amt_a} paise ({txn_a.source.value}) vs {amt_b} paise ({txn_b.source.value}).",
                            details={
                                "reference": str(ref_a),
                                "source_a": txn_a.source.value,
                                "amount_a": amt_a,
                                "source_b": txn_b.source.value,
                                "amount_b": amt_b,
                            }
                        )
                    )
            elif amt_a == amt_b and days_diff <= 1:
                # Same exact amount within 1 day across different connected sources
                is_match = True
            elif diff_pct <= DEDUP_AMOUNT_TOLERANCE_PCT and (txn_a.source == DataSourceType.POS or txn_b.source == DataSourceType.POS):
                # POS MDR settlement variance
                is_match = True

            if is_match:
                # Merge into canonical economic event
                cross_source_matches += 1
                used_in_cross_source.add(txn_b.transaction_id)

                group_hash = hashlib.md5(f"{txn_a.transaction_id}_{txn_b.transaction_id}".encode("utf-8")).hexdigest()[:8].upper()
                group_id = txn_a.duplicate_group_id or f"DG-{group_hash}"
                txn_a.duplicate_group_id = group_id
                txn_a.linked_transaction_ids.append(txn_b.transaction_id)
                txn_a.provenance = merge_provenances(txn_a.provenance, txn_b.provenance)

                # Inherit higher-confidence category and verification from txn_b if applicable
                if txn_b.category_confidence > txn_a.category_confidence and txn_b.category not in (TransactionCategory.UNCLASSIFIED, TransactionCategory.SELF_DECLARED_CASH_INCOME):
                    txn_a.category = txn_b.category
                    txn_a.category_confidence = max(txn_a.category_confidence, txn_b.category_confidence)
                    txn_a.category_source = txn_b.category_source
                    txn_a.verification = txn_b.verification
                    if txn_b.mode != TransactionMode.OTHER:
                        txn_a.mode = txn_b.mode
                    if txn_b.counterparty_name:
                        txn_a.counterparty_name = txn_a.counterparty_name or txn_b.counterparty_name
                    if txn_b.narration:
                        txn_a.narration = txn_a.narration or txn_b.narration

                # Elevate verification level and confidence due to independent cross-source corroboration
                if txn_b.source in (DataSourceType.INVOICE, DataSourceType.SUPPLIER_RECORD, DataSourceType.RECEIPT):
                    txn_a.verification = VerificationLevel.DOCUMENT_MATCHED
                    txn_a.category = TransactionCategory.BUSINESS_INCOME if txn_a.direction == "CREDIT" else TransactionCategory.BUSINESS_EXPENSE
                    txn_a.category_source = CategorySource.INVOICE_MATCH
                    txn_a.category_confidence = max(txn_a.category_confidence, 0.95)
                elif txn_b.source == DataSourceType.BUSINESS_LEDGER:
                    txn_a.verification = VerificationLevel.LEDGER_MATCHED
                    txn_a.category = TransactionCategory.BUSINESS_INCOME if txn_a.direction == "CREDIT" else TransactionCategory.BUSINESS_EXPENSE
                    txn_a.category_source = CategorySource.LEDGER_MATCH
                    txn_a.category_confidence = max(txn_a.category_confidence, 0.92)
                else:
                    if txn_a.verification not in (VerificationLevel.DOCUMENT_MATCHED, VerificationLevel.LEDGER_MATCHED, VerificationLevel.MERCHANT_MATCHED):
                        txn_a.verification = VerificationLevel.CROSS_SOURCE_CORROBORATED
                    if txn_a.category_source == CategorySource.NONE:
                        txn_a.category_source = CategorySource.CROSS_SOURCE_MATCH
                    txn_a.category_confidence = min(1.0, txn_a.category_confidence + 0.10)

                # Upgrade self-declared cash if corroborated by connected source
                if txn_a.category == TransactionCategory.SELF_DECLARED_CASH_INCOME:
                    txn_a.category = TransactionCategory.BUSINESS_INCOME if txn_a.direction == "CREDIT" else TransactionCategory.BUSINESS_EXPENSE

                # Only set model_eligible = True if category is a verified business category
                if txn_a.category not in (TransactionCategory.UNCLASSIFIED, TransactionCategory.SELF_DECLARED_CASH_INCOME, TransactionCategory.TRANSFER):
                    txn_a.model_eligible = True
                else:
                    txn_a.model_eligible = False

        canonical_list.append(txn_a)

    dedup_stats = {
        "total_input_records": len(transactions),
        "exact_duplicates": exact_duplicates,
        "fingerprint_duplicates": fingerprint_duplicates,
        "cross_source_matches": cross_source_matches,
        "canonical_economic_events": len(canonical_list),
    }

    return canonical_list, conflicts, dedup_stats
