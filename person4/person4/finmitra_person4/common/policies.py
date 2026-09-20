"""
common/policies.py

Profile-level policy functions applied by the Profile Assembler.

These are separate from the capacity-specific policy (CapacityPolicy) and
implement the FinMitra specification rules for readiness-index calculation,
policy ceilings, and confidence fusion.

Every function is pure (no side effects) and deterministic.
"""
from __future__ import annotations

from typing import List, Set, Tuple

from common.schemas import (
    CashflowResult,
    CapacityResult,
    EvidenceResult,
    RepaymentResult,
)


# ---------------------------------------------------------------------------
# Readiness index
# ---------------------------------------------------------------------------

#: Weights as specified in the FinMitra design.
CASHFLOW_WEIGHT: float = 0.55
REPAYMENT_WEIGHT: float = 0.45

#: Hard-block ceiling when the repayment engine blocks new credit.
REPAYMENT_BLOCK_CEILING: float = 35.0

#: Ceiling applied when the evidence grade is D.
EVIDENCE_GRADE_D_CEILING: float = 75.0


def compute_readiness_index(
    cashflow: CashflowResult,
    repayment: RepaymentResult,
) -> float:
    """
    Compute the raw readiness index from cash-flow and repayment scores.

    Formula (from FinMitra spec):
        readiness_index = 0.55 × cashflow.score + 0.45 × repayment.score

    The returned value is in [0, 100] by construction (both scores are in
    [0, 100] and the weights sum to 1.0).
    """
    return CASHFLOW_WEIGHT * cashflow.score + REPAYMENT_WEIGHT * repayment.score


def apply_repayment_block_ceiling(
    readiness_index: float,
    repayment: RepaymentResult,
) -> Tuple[float, bool]:
    """
    Apply the hard repayment-block ceiling.

    If repayment.new_credit_blocked is True the readiness index is capped at
    REPAYMENT_BLOCK_CEILING (35).  This is a hard policy rule — it cannot be
    overridden by high income or strong cash flow.

    Returns:
        (adjusted_index, ceiling_was_applied)
    """
    if repayment.new_credit_blocked:
        return min(readiness_index, REPAYMENT_BLOCK_CEILING), True
    return readiness_index, False


def apply_evidence_grade_d_ceiling(
    readiness_index: float,
    evidence: EvidenceResult,
) -> Tuple[float, bool]:
    """
    Apply the Evidence Grade D ceiling.

    If evidence.evidence_grade == 'D' the readiness index is capped at
    EVIDENCE_GRADE_D_CEILING (75).

    Returns:
        (adjusted_index, ceiling_was_applied)
    """
    if evidence.evidence_grade == "D":
        return min(readiness_index, EVIDENCE_GRADE_D_CEILING), True
    return readiness_index, False


def apply_insufficient_history(
    evidence: EvidenceResult,
) -> bool:
    """
    Return True when the evidence engine indicates insufficient history.

    When True the Profile Assembler must set readiness_index to None.
    """
    return evidence.insufficient_history


# ---------------------------------------------------------------------------
# Confidence fusion
# ---------------------------------------------------------------------------


def fuse_confidence(
    evidence: EvidenceResult,
    cashflow: CashflowResult,
    repayment: RepaymentResult,
    capacity: CapacityResult,
) -> float:
    """
    Overall profile confidence = min of all component confidences.

    Per spec: the weakest component constrains the overall confidence.
    Do NOT average or multiply — take the minimum.
    """
    return min(
        evidence.confidence,
        cashflow.confidence,
        repayment.confidence,
        capacity.confidence,
    )


# ---------------------------------------------------------------------------
# Warning consolidation
# ---------------------------------------------------------------------------


def consolidate_warnings(
    evidence: EvidenceResult,
    cashflow: CashflowResult,
    repayment: RepaymentResult,
    capacity: CapacityResult,
    policy_flags: List[str],
) -> List[str]:
    """Collect and deduplicate warnings from all components plus policy flags."""
    seen: Set[str] = set()
    consolidated: List[str] = []

    for warning in (
        *evidence.warnings,
        *cashflow.warnings,
        *repayment.warnings,
        *capacity.warnings,
        *policy_flags,
    ):
        if warning not in seen:
            seen.add(warning)
            consolidated.append(warning)

    return consolidated
