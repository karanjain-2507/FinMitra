"""
Evidence Corroboration and Metric Extraction.
Measures cross-source coverage, corroboration depth, and source diversity.
"""
from __future__ import annotations
from typing import List, Dict, Any, Set
from datetime import date

from ..enums import VerificationLevel, DataSourceType, TransactionCategory
from ..schemas import NormalizedTransaction


def compute_corroboration_metrics(
    transactions: List[NormalizedTransaction],
    source_count: int
) -> Dict[str, Any]:
    """
    Compute structured corroboration and coverage metrics from transaction timeline.
    """
    if not transactions:
        return {
            "coverage_days": 0,
            "active_months": 0,
            "total_transactions": 0,
            "verified_transaction_count": 0,
            "unclassified_transaction_count": 0,
            "self_declared_transaction_count": 0,
            "corroborated_count": 0,
            "corroboration_rate": 0.0,
            "source_count": source_count,
            "cross_source_match_rate": 0.0,
            "verified_ratio": 0.0,
        }

    dates = [t.date for t in transactions]
    min_date = min(dates)
    max_date = max(dates)
    coverage_days = (max_date - min_date).days + 1

    # Active months calculation (distinct Year-Month tuples)
    active_months_set: Set[str] = {f"{d.year}-{d.month:02d}" for d in dates}
    active_months = len(active_months_set)

    total_count = len(transactions)
    verified_count = sum(
        1 for t in transactions
        if t.verification in (
            VerificationLevel.CROSS_SOURCE_CORROBORATED,
            VerificationLevel.DOCUMENT_MATCHED,
            VerificationLevel.LEDGER_MATCHED,
            VerificationLevel.MERCHANT_MATCHED
        )
    )
    unclassified_count = sum(1 for t in transactions if t.category == TransactionCategory.UNCLASSIFIED)
    self_declared_count = sum(1 for t in transactions if t.category == TransactionCategory.SELF_DECLARED_CASH_INCOME)
    
    corroborated_count = sum(
        1 for t in transactions
        if t.verification == VerificationLevel.CROSS_SOURCE_CORROBORATED
        or bool(t.linked_transaction_ids)
    )

    corroboration_rate = round(corroborated_count / total_count, 4) if total_count > 0 else 0.0
    verified_ratio = round(verified_count / total_count, 4) if total_count > 0 else 0.0

    return {
        "coverage_days": coverage_days,
        "active_months": active_months,
        "total_transactions": total_count,
        "verified_transaction_count": verified_count,
        "unclassified_transaction_count": unclassified_count,
        "self_declared_transaction_count": self_declared_count,
        "corroborated_count": corroborated_count,
        "corroboration_rate": corroboration_rate,
        "source_count": source_count,
        "cross_source_match_rate": corroboration_rate,
        "verified_ratio": verified_ratio,
        "start_date": str(min_date),
        "end_date": str(max_date),
    }
