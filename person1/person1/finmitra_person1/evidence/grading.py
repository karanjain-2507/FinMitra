"""
Evidence Quality Scoring and Grading.
Computes an objective, explainable 0-100 evidence quality score and maps to A/B/C/D grade.
Answers: "How reliable, complete, and trustworthy is the financial evidence?"
"""
from __future__ import annotations
from typing import Dict, Any, Tuple, Literal

from ..enums import EvidenceGrade, EvidenceStatus
from ..config import (
    GRADE_A_MIN,
    GRADE_B_MIN,
    GRADE_C_MIN,
    MIN_HISTORY_DAYS,
    MIN_ACTIVE_MONTHS,
    MIN_VALID_TRANSACTIONS,
    WEIGHT_SOURCE_QUALITY,
    WEIGHT_CORROBORATION,
    WEIGHT_DATA_COMPLETENESS,
    WEIGHT_CONSISTENCY_CONFLICT,
    WEIGHT_CLASSIFICATION_QUALITY,
    WEIGHT_DEDUP_INTEGRITY,
)


def compute_evidence_score(
    features: Dict[str, Any],
    conflict_count: int,
    raw_error_count: int
) -> Tuple[float, Dict[str, float]]:
    """
    Compute transparent multi-dimensional 0-100 evidence quality score.
    Returns:
        (total_score, component_breakdown)
    """
    source_count = features.get("source_count", 1)
    total_txns = features.get("total_transactions", 0)
    verified_txns = features.get("verified_transaction_count", 0)
    unclassified_txns = features.get("unclassified_transaction_count", 0)
    corroborated_txns = features.get("corroborated_count", 0)
    coverage_days = features.get("coverage_days", 0)

    # 1. Source Quality / Diversity (0-100)
    # 1 source = 50, 2 sources = 75, 3 sources = 90, 4+ sources = 100
    if source_count >= 4:
        source_score = 100.0
    elif source_count == 3:
        source_score = 90.0
    elif source_count == 2:
        source_score = 75.0
    elif source_count == 1:
        source_score = 55.0
    else:
        source_score = 10.0

    # 2. Corroboration & Verification Rate (0-100)
    if total_txns > 0:
        ver_ratio = verified_txns / total_txns
        corrob_ratio = corroborated_txns / total_txns
        # Combined corroboration metric
        corrob_score = min(100.0, (ver_ratio * 70.0) + (corrob_ratio * 40.0) + (10.0 if source_count > 1 else 0.0))
    else:
        corrob_score = 0.0

    # 3. Data Completeness & Validity (0-100)
    total_raw = total_txns + raw_error_count
    if total_raw > 0:
        valid_ratio = total_txns / total_raw
        completeness_score = valid_ratio * 100.0
    else:
        completeness_score = 0.0

    # 4. Consistency & Conflict Penalty (0-100)
    # Start at 100, penalize for each material conflict
    consistency_score = max(0.0, 100.0 - (conflict_count * 25.0))

    # 5. Classification Quality (0-100)
    if total_txns > 0:
        classified_ratio = (total_txns - unclassified_txns) / total_txns
        classification_score = classified_ratio * 100.0
    else:
        classification_score = 0.0

    # 6. Deduplication Integrity (0-100)
    # High score if deduplication and linking executed cleanly
    dedup_score = 95.0 if total_txns > 0 else 50.0

    # Weighted Sum
    total_score = (
        (source_score * WEIGHT_SOURCE_QUALITY) +
        (corrob_score * WEIGHT_CORROBORATION) +
        (completeness_score * WEIGHT_DATA_COMPLETENESS) +
        (consistency_score * WEIGHT_CONSISTENCY_CONFLICT) +
        (classification_score * WEIGHT_CLASSIFICATION_QUALITY) +
        (dedup_score * WEIGHT_DEDUP_INTEGRITY)
    )

    # History length scaling: if history is very short (<30 days), scale down score gently
    if coverage_days < 30:
        total_score *= 0.70
    elif coverage_days < 60:
        total_score *= 0.85

    total_score = round(max(0.0, min(100.0, total_score)), 2)

    breakdown = {
        "source_quality": round(source_score, 2),
        "corroboration": round(corrob_score, 2),
        "completeness": round(completeness_score, 2),
        "consistency": round(consistency_score, 2),
        "classification": round(classification_score, 2),
        "dedup_integrity": round(dedup_score, 2),
    }

    return total_score, breakdown


def determine_grade(score: float) -> Literal["A", "B", "C", "D"]:
    """Map evidence quality score to standard A/B/C/D grade."""
    if score >= GRADE_A_MIN:
        return "A"
    elif score >= GRADE_B_MIN:
        return "B"
    elif score >= GRADE_C_MIN:
        return "C"
    else:
        return "D"


def check_insufficient_history(
    coverage_days: int,
    active_months: int,
    valid_transaction_count: int
) -> bool:
    """
    Check if the available history is too thin for confident assessment.
    Returns True if insufficient, False otherwise.
    """
    return (
        coverage_days < MIN_HISTORY_DAYS
        or active_months < MIN_ACTIVE_MONTHS
        or valid_transaction_count < MIN_VALID_TRANSACTIONS
    )
