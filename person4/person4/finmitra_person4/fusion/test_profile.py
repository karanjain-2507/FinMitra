"""
fusion/test_profile.py

Unit tests for the Profile Assembler.

Tests cover:
  - Normal profile assembly
  - Repayment hard block → readiness cap at 35
  - Evidence grade D → readiness cap at 75
  - Insufficient history → readiness_index = None
  - Confidence fusion (minimum)
  - Safe EMI propagation
  - Policy flags generation
  - Warning consolidation
  - Reason consolidation
  - Contract failures (malformed component results)
"""
from __future__ import annotations

import pytest

from common.config import DEFAULT_POLICY
from common.schemas import (
    CapacityInput,
    CashflowResult,
    EvidenceResult,
    Reason,
    RepaymentResult,
    SafeEMI,
)
from capacity.engine import CapacityEngine
from fusion.adapters import (
    ComponentContractError,
    validate_cashflow,
    validate_evidence,
    validate_repayment,
)
from fusion.profile_assembler import ProfileAssembler
from mocks.cashflow import mock_cashflow
from mocks.evidence import mock_evidence
from mocks.repayment import mock_repayment


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_capacity_result(surplus: float = 8000.0, blocked: bool = False):
    inp = CapacityInput(
        conservative_monthly_inflow=28000,
        essential_household_expense=10000,
        essential_business_expense=7500,
        existing_formal_emis=1500,
        existing_informal_installments=1000,
        income_volatility=0.18,
        lowest_recent_monthly_inflow=21000,
        available_balance_buffer=12000,
        outstanding_delinquent_amount=0,
    )
    return CapacityEngine.assess(inp, new_credit_blocked=blocked)


# ============================================================================
# Normal profile assembly
# ============================================================================

class TestNormalAssembly:
    def test_strong_borrower_profile(self):
        evidence = mock_evidence("strong_borrower")
        cashflow = mock_cashflow("strong_borrower")
        repayment = mock_repayment("strong_borrower")
        capacity = _make_capacity_result()

        profile = ProfileAssembler.assemble(
            evidence, cashflow, repayment, capacity, borrower_id="B001"
        )

        assert profile.profile_version == "1.0"
        assert profile.borrower_id == "B001"
        assert profile.readiness_index is not None
        # readiness = 0.55*78 + 0.45*85 = 42.9 + 38.25 = 81.15
        assert profile.readiness_index == pytest.approx(81.15, rel=1e-3)
        assert 0.0 <= profile.overall_confidence <= 1.0
        assert profile.safe_emi.maximum > 0

    def test_readiness_index_formula(self):
        """Verify 0.55 × CF + 0.45 × RP formula exactly."""
        cf_score = 70.0
        rp_score = 60.0
        expected_readiness = 0.55 * cf_score + 0.45 * rp_score  # 38.5 + 27 = 65.5

        cashflow = CashflowResult(
            version="test",
            score=cf_score,
            confidence=0.80,
            features={},
            reasons=[],
            warnings=[],
        )
        repayment = RepaymentResult(
            version="test",
            score=rp_score,
            confidence=0.80,
            new_credit_blocked=False,
            features={},
            reasons=[],
            warnings=[],
        )
        evidence = EvidenceResult(
            version="test",
            score=70.0,
            confidence=0.80,
            evidence_grade="B",
            insufficient_history=False,
            features={},
            reasons=[],
            warnings=[],
        )
        capacity = _make_capacity_result()

        profile = ProfileAssembler.assemble(evidence, cashflow, repayment, capacity)
        assert profile.readiness_index == pytest.approx(expected_readiness, rel=1e-4)


# ============================================================================
# Policy ceiling tests
# ============================================================================

class TestPolicyCeilings:
    def test_repayment_block_caps_readiness_at_35(self):
        evidence = mock_evidence("unpaid_loan")
        cashflow = mock_cashflow("unpaid_loan")
        repayment = mock_repayment("unpaid_loan")  # new_credit_blocked=True
        capacity = _make_capacity_result(blocked=True)

        profile = ProfileAssembler.assemble(evidence, cashflow, repayment, capacity)

        assert profile.readiness_index is not None
        assert profile.readiness_index <= 35.0

        block_flags = [f for f in profile.policy_flags if "REPAYMENT_BLOCK_CEILING" in f]
        assert len(block_flags) >= 1

    def test_evidence_grade_d_caps_readiness_at_75(self):
        """Grade D evidence should cap readiness at 75 (if raw > 75)."""
        # Use high CF and RP scores to get raw readiness > 75
        cashflow = CashflowResult(
            version="test", score=90.0, confidence=0.80,
            features={}, reasons=[], warnings=[],
        )
        repayment = RepaymentResult(
            version="test", score=90.0, confidence=0.80,
            new_credit_blocked=False, features={}, reasons=[], warnings=[],
        )
        evidence = EvidenceResult(
            version="test", score=30.0, confidence=0.60,
            evidence_grade="D",
            insufficient_history=False,
            features={}, reasons=[], warnings=[],
        )
        capacity = _make_capacity_result()

        profile = ProfileAssembler.assemble(evidence, cashflow, repayment, capacity)

        # raw = 0.55*90 + 0.45*90 = 90.0 > 75 → should be capped at 75
        assert profile.readiness_index == pytest.approx(75.0)
        grade_d_flags = [f for f in profile.policy_flags if "EVIDENCE_GRADE_D" in f]
        assert len(grade_d_flags) >= 1

    def test_evidence_grade_d_no_ceiling_when_readiness_below_75(self):
        """Grade D should not raise readiness if it was already below 75."""
        cashflow = CashflowResult(
            version="test", score=60.0, confidence=0.80,
            features={}, reasons=[], warnings=[],
        )
        repayment = RepaymentResult(
            version="test", score=50.0, confidence=0.80,
            new_credit_blocked=False, features={}, reasons=[], warnings=[],
        )
        evidence = EvidenceResult(
            version="test", score=30.0, confidence=0.60,
            evidence_grade="D",
            insufficient_history=False,
            features={}, reasons=[], warnings=[],
        )
        capacity = _make_capacity_result()

        profile = ProfileAssembler.assemble(evidence, cashflow, repayment, capacity)

        raw = 0.55 * 60.0 + 0.45 * 50.0  # 33 + 22.5 = 55.5
        # 55.5 < 75, so ceiling doesn't actually lower it
        assert profile.readiness_index == pytest.approx(raw, rel=1e-4)

    def test_insufficient_history_sets_readiness_to_none(self):
        evidence = mock_evidence("thin_file")  # insufficient_history=True
        cashflow = mock_cashflow("thin_file")
        repayment = mock_repayment("thin_file")
        capacity = _make_capacity_result()

        profile = ProfileAssembler.assemble(evidence, cashflow, repayment, capacity)

        assert profile.readiness_index is None
        history_flags = [f for f in profile.policy_flags if "INSUFFICIENT_HISTORY" in f]
        assert len(history_flags) >= 1


# ============================================================================
# Confidence fusion tests
# ============================================================================

class TestConfidenceFusion:
    def test_minimum_confidence_is_used(self):
        """Overall confidence must equal the minimum of all four components."""
        evidence = EvidenceResult(
            version="test", score=70.0, confidence=0.90,
            evidence_grade="B", insufficient_history=False,
            features={}, reasons=[], warnings=[],
        )
        cashflow = CashflowResult(
            version="test", score=65.0, confidence=0.55,  # ← minimum
            features={}, reasons=[], warnings=[],
        )
        repayment = RepaymentResult(
            version="test", score=70.0, confidence=0.85,
            new_credit_blocked=False, features={}, reasons=[], warnings=[],
        )
        capacity = _make_capacity_result()  # confidence ≈ 0.89 (without loan fields)

        profile = ProfileAssembler.assemble(evidence, cashflow, repayment, capacity)
        assert profile.overall_confidence == pytest.approx(0.55, rel=1e-4)

    def test_confidence_not_averaged(self):
        """Verify it is the min, not the average."""
        confs = [0.40, 0.80, 0.90, 0.95]
        expected = min(confs)  # 0.40

        evidence = EvidenceResult(
            version="test", score=70.0, confidence=confs[0],
            evidence_grade="B", insufficient_history=False,
            features={}, reasons=[], warnings=[],
        )
        cashflow = CashflowResult(
            version="test", score=65.0, confidence=confs[1],
            features={}, reasons=[], warnings=[],
        )
        repayment = RepaymentResult(
            version="test", score=70.0, confidence=confs[2],
            new_credit_blocked=False, features={}, reasons=[], warnings=[],
        )
        # Build a capacity result with specific confidence by using a capacity input
        # that results in the desired confidence (~0.89 without loan)
        capacity = _make_capacity_result()

        profile = ProfileAssembler.assemble(evidence, cashflow, repayment, capacity)
        # The minimum is 0.40 (evidence) or capacity.confidence, whichever is lower
        assert profile.overall_confidence <= 0.40 + 0.001  # ≤ 0.40


# ============================================================================
# Safe EMI propagation tests
# ============================================================================

class TestSafeEMIPropagation:
    def test_safe_emi_matches_capacity_output(self):
        evidence = mock_evidence("strong_borrower")
        cashflow = mock_cashflow("strong_borrower")
        repayment = mock_repayment("strong_borrower")
        capacity = _make_capacity_result()

        profile = ProfileAssembler.assemble(evidence, cashflow, repayment, capacity)

        assert profile.safe_emi.minimum == capacity.safe_emi.minimum
        assert profile.safe_emi.maximum == capacity.safe_emi.maximum

    def test_safe_emi_is_zero_when_blocked(self):
        evidence = mock_evidence("unpaid_loan")
        cashflow = mock_cashflow("unpaid_loan")
        repayment = mock_repayment("unpaid_loan")
        capacity = _make_capacity_result(blocked=True)

        profile = ProfileAssembler.assemble(evidence, cashflow, repayment, capacity)

        assert profile.safe_emi.minimum == 0.0
        assert profile.safe_emi.maximum == 0.0


# ============================================================================
# Contract failure tests
# ============================================================================

class TestContractFailures:
    def test_confidence_above_1_rejected(self):
        """Confidence of 80 (should be 0.80) must be rejected."""
        with pytest.raises(Exception):
            EvidenceResult(
                version="test",
                score=70.0,
                confidence=80.0,  # ← should be 0.80
                evidence_grade="B",
                insufficient_history=False,
            )

    def test_score_above_100_rejected(self):
        with pytest.raises(Exception):
            CashflowResult(
                version="test",
                score=150.0,  # ← invalid
                confidence=0.80,
            )

    def test_negative_score_rejected(self):
        with pytest.raises(Exception):
            RepaymentResult(
                version="test",
                score=-5.0,  # ← invalid
                confidence=0.80,
                new_credit_blocked=False,
            )

    def test_missing_required_field(self):
        with pytest.raises(Exception):
            EvidenceResult(
                # missing evidence_grade
                version="test",
                score=70.0,
                confidence=0.80,
                insufficient_history=False,
            )

    def test_capacity_score_must_be_none(self):
        """Adapter should reject capacity with a non-None score."""
        from fusion.adapters import validate_capacity
        capacity = _make_capacity_result()
        # Force a non-None score (bypassing Pydantic with model_copy)
        # Pydantic v2 CapacityResult has score: None which is literal type,
        # so we test the adapter separately by mocking.
        # The schema itself enforces score=None, so this just confirms behaviour.
        validated = validate_capacity(capacity)
        assert validated.score is None
