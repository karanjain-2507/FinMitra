"""
fusion/profile_assembler.py

The Profile Assembler — combines the four component outputs into the final
FinMitra Credit Evidence Profile.

Architecture (from the FinMitra specification):
  EvidenceResult
  CashflowResult
  RepaymentResult
  CapacityResult
        │
        ▼
  ProfileAssembler.assemble()
        │
        ▼
  FinMitraCreditEvidenceProfile

Responsibilities:
  1. Validate component contracts (via fusion.adapters).
  2. Calculate readiness index (0.55 × CF + 0.45 × RP).
  3. Apply policy ceilings (repayment block, evidence grade D).
  4. Set readiness_index to None for insufficient history.
  5. Fuse confidence (minimum of all four components).
  6. Carry safe_emi from Capacity Engine.
  7. Consolidate warnings and reasons.
  8. Produce FinMitraCreditEvidenceProfile.

The assembler must NOT:
  - Retrain anything.
  - Average all four scores.
  - Modify component features.
  - Reinterpret evidence.
  - Hide negative signals.
"""
from __future__ import annotations

from typing import List, Optional

from common.policies import (
    apply_evidence_grade_d_ceiling,
    apply_insufficient_history,
    apply_repayment_block_ceiling,
    compute_readiness_index,
    consolidate_warnings,
    fuse_confidence,
)
from common.schemas import (
    CapacityResult,
    CashflowResult,
    EvidenceResult,
    FinMitraCreditEvidenceProfile,
    Reason,
    RepaymentResult,
)
from fusion.adapters import validate_all_components


class ProfileAssembler:
    """
    Assembles the final FinMitra Credit Evidence Profile from four
    validated component results.

    Usage::

        from fusion.profile_assembler import ProfileAssembler

        profile = ProfileAssembler.assemble(
            evidence=evidence_result,
            cashflow=cashflow_result,
            repayment=repayment_result,
            capacity=capacity_result,
            borrower_id="B001",
        )
    """

    PROFILE_VERSION: str = "1.0"

    @classmethod
    def assemble(
        cls,
        evidence: EvidenceResult,
        cashflow: CashflowResult,
        repayment: RepaymentResult,
        capacity: CapacityResult,
        borrower_id: Optional[str] = None,
    ) -> FinMitraCreditEvidenceProfile:
        """
        Assemble the final profile.

        Args:
            evidence   : Validated EvidenceResult from Person 1.
            cashflow   : Validated CashflowResult from Person 2.
            repayment  : Validated RepaymentResult from Person 3.
            capacity   : Validated CapacityResult from Person 4.
            borrower_id: Optional borrower identifier for traceability.

        Returns:
            FinMitraCreditEvidenceProfile — the complete, assembled profile.

        Raises:
            ComponentContractError: if any component result violates its contract.
        """
        # ------------------------------------------------------------------
        # Step 1 — Validate all component contracts
        # ------------------------------------------------------------------
        evidence, cashflow, repayment, capacity = validate_all_components(
            evidence, cashflow, repayment, capacity
        )

        # ------------------------------------------------------------------
        # Step 2 — Readiness index
        # Computed from cashflow + repayment ONLY (per spec).
        # ------------------------------------------------------------------
        policy_flags: List[str] = []

        if apply_insufficient_history(evidence):
            readiness_index = None
            policy_flags.append(
                "INSUFFICIENT_HISTORY: Evidence indicates insufficient transaction "
                "history. Readiness index set to None."
            )
        else:
            raw_readiness = compute_readiness_index(cashflow, repayment)

            # Apply repayment hard-block ceiling
            readiness_index, block_applied = apply_repayment_block_ceiling(
                raw_readiness, repayment
            )
            if block_applied:
                policy_flags.append(
                    f"REPAYMENT_BLOCK_CEILING: new_credit_blocked=True. "
                    f"Readiness index capped at {readiness_index:.1f} "
                    f"(was {raw_readiness:.1f})."
                )

            # Apply evidence grade D ceiling
            readiness_index, grade_d_applied = apply_evidence_grade_d_ceiling(
                readiness_index, evidence
            )
            if grade_d_applied:
                policy_flags.append(
                    f"EVIDENCE_GRADE_D_CEILING: Evidence grade D detected. "
                    f"Readiness index capped at {readiness_index:.1f}."
                )

        # ------------------------------------------------------------------
        # Step 3 — Confidence fusion
        # Overall confidence = min of all four component confidences.
        # ------------------------------------------------------------------
        overall_confidence = fuse_confidence(evidence, cashflow, repayment, capacity)

        # ------------------------------------------------------------------
        # Step 4 — Safe EMI (passed through from Capacity Engine)
        # ------------------------------------------------------------------
        safe_emi = capacity.safe_emi

        # ------------------------------------------------------------------
        # Step 5 — Consolidate reasons and warnings
        # ------------------------------------------------------------------
        final_reasons = cls._consolidate_reasons(
            evidence, cashflow, repayment, capacity
        )
        final_warnings = consolidate_warnings(
            evidence, cashflow, repayment, capacity, policy_flags
        )

        # ------------------------------------------------------------------
        # Step 6 — Assemble and return
        # ------------------------------------------------------------------
        return FinMitraCreditEvidenceProfile(
            profile_version=cls.PROFILE_VERSION,
            borrower_id=borrower_id,
            readiness_index=(
                round(readiness_index, 2) if readiness_index is not None else None
            ),
            overall_confidence=round(overall_confidence, 4),
            evidence=evidence,
            cashflow=cashflow,
            repayment=repayment,
            capacity=capacity,
            safe_emi=safe_emi,
            policy_flags=policy_flags,
            final_reasons=final_reasons,
            final_warnings=final_warnings,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _consolidate_reasons(
        evidence: EvidenceResult,
        cashflow: CashflowResult,
        repayment: RepaymentResult,
        capacity: CapacityResult,
    ) -> List[Reason]:
        """
        Merge reasons from all four components into a single list.

        Ordering: Evidence → Cashflow → Repayment → Capacity
        (i.e. upstream components first, capacity last).
        """
        return [
            *evidence.reasons,
            *cashflow.reasons,
            *repayment.reasons,
            *capacity.reasons,
        ]
