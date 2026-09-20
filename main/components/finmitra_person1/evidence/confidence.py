"""
Evidence Confidence Computation.
Computes a normalized 0.0 - 1.0 confidence value reflecting the certainty
and statistical robustness of the evidence profile.
"""
from __future__ import annotations
from typing import Dict, Any

from ..config import MIN_HISTORY_DAYS, MIN_ACTIVE_MONTHS, MIN_VALID_TRANSACTIONS


def compute_evidence_confidence(
    features: Dict[str, Any],
    evidence_score: float,
    insufficient_history: bool,
    conflict_count: int
) -> float:
    """
    Compute evidence confidence between 0.0 and 1.0.
    """
    coverage_days = features.get("coverage_days", 0)
    source_count = features.get("source_count", 1)
    total_txns = features.get("total_transactions", 0)
    corroboration_rate = features.get("corroboration_rate", 0.0)
    verified_ratio = features.get("verified_ratio", 0.0)

    # Base factor from evidence score
    base_conf = (evidence_score / 100.0) * 0.40

    # History factor (up to 0.30)
    history_factor = min(1.0, coverage_days / (MIN_HISTORY_DAYS * 1.5)) * 0.15
    txn_vol_factor = min(1.0, total_txns / (MIN_VALID_TRANSACTIONS * 2.0)) * 0.15

    # Source diversity factor (up to 0.15)
    source_factor = min(1.0, source_count / 3.0) * 0.15

    # Corroboration & verification factor (up to 0.15)
    corrob_factor = ((corroboration_rate * 0.5) + (verified_ratio * 0.5)) * 0.15

    confidence = base_conf + history_factor + txn_vol_factor + source_factor + corrob_factor

    # Penalize for conflicts
    if conflict_count > 0:
        confidence -= (conflict_count * 0.10)

    # If insufficient history is flagged, cap confidence
    if insufficient_history:
        confidence = min(confidence, 0.45)

    return round(max(0.05, min(0.99, confidence)), 4)
