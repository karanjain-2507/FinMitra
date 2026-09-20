"""
fusion/adapters.py

Contract validation adapters for each upstream component result.

These adapters sit between the raw component outputs and the Profile Assembler.
They:
  1. Validate that the component result satisfies its public contract.
  2. Fail loudly (raise ComponentContractError) on violations.
  3. Do NOT modify or interpret component data beyond validation.

The Profile Assembler calls these adapters before consuming any component result.
"""
from __future__ import annotations

from typing import Tuple

from common.schemas import (
    CapacityResult,
    CashflowResult,
    EvidenceResult,
    RepaymentResult,
)
from common.validation import ComponentContractError, validate_component_result


def validate_evidence(evidence: EvidenceResult) -> EvidenceResult:
    """Validate the Evidence Engine output contract."""
    validate_component_result(evidence, "evidence")
    # evidence-specific: evidence_grade must be A/B/C/D
    if evidence.evidence_grade not in ("A", "B", "C", "D"):
        raise ComponentContractError(
            "evidence",
            f"evidence_grade must be one of A/B/C/D; got {evidence.evidence_grade!r}",
        )
    return evidence


def validate_cashflow(cashflow: CashflowResult) -> CashflowResult:
    """Validate the Cash-Flow Model output contract."""
    validate_component_result(cashflow, "cashflow")
    # A thin file legitimately has no cash-flow score. The profile assembler
    # represents that uncertainty with readiness_index=None instead of inventing
    # a neutral score.
    return cashflow


def validate_repayment(repayment: RepaymentResult) -> RepaymentResult:
    """Validate the Repayment Engine output contract."""
    validate_component_result(repayment, "repayment")
    # repayment-specific: score is required
    if repayment.score is None:
        raise ComponentContractError(
            "repayment",
            "repayment.score must be a number (0–100); it contributes to the "
            "readiness index and cannot be None.",
        )
    # new_credit_blocked must be a bool
    if not isinstance(repayment.new_credit_blocked, bool):
        raise ComponentContractError(
            "repayment",
            f"new_credit_blocked must be a bool; got {type(repayment.new_credit_blocked).__name__}",
        )
    return repayment


def validate_capacity(capacity: CapacityResult) -> CapacityResult:
    """Validate the Capacity Engine output contract."""
    validate_component_result(capacity, "capacity")
    # score is intentionally None for capacity
    if capacity.score is not None:
        raise ComponentContractError(
            "capacity",
            f"capacity.score must be None (capacity produces amounts, not scores); "
            f"got {capacity.score}",
        )
    # safe_emi must be present
    if capacity.safe_emi is None:
        raise ComponentContractError("capacity", "safe_emi is required")
    if capacity.safe_emi.minimum < 0 or capacity.safe_emi.maximum < 0:
        raise ComponentContractError(
            "capacity",
            "safe_emi values must be ≥ 0",
        )
    return capacity


def validate_all_components(
    evidence: EvidenceResult,
    cashflow: CashflowResult,
    repayment: RepaymentResult,
    capacity: CapacityResult,
) -> Tuple[EvidenceResult, CashflowResult, RepaymentResult, CapacityResult]:
    """
    Validate all four component results in one call.

    Returns the validated results unchanged.
    Raises ComponentContractError on the first violation found.
    """
    return (
        validate_evidence(evidence),
        validate_cashflow(cashflow),
        validate_repayment(repayment),
        validate_capacity(capacity),
    )
