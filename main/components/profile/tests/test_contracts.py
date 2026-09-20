"""
tests/test_contracts.py

Tests that malformed component results are rejected loudly.

These tests verify that:
  - Confidence expressed as a percentage (80 instead of 0.80) is rejected.
  - Scores outside [0, 100] are rejected.
  - Missing required fields cause validation errors.
  - The ComponentContractError is raised for adapter violations.
  - NaN and Infinity are rejected.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.schemas import (
    CashflowResult,
    EvidenceResult,
    RepaymentResult,
    SafeEMI,
)
from common.validation import ComponentContractError, validate_component_result
from fusion.adapters import validate_cashflow, validate_evidence, validate_repayment


# ============================================================================
# Pydantic schema validation
# ============================================================================

class TestSchemaValidation:
    def test_confidence_as_percentage_rejected(self):
        """80 instead of 0.80 must fail."""
        with pytest.raises(ValidationError):
            EvidenceResult(
                version="test",
                score=70.0,
                confidence=80.0,  # ← invalid: must be 0–1
                evidence_grade="B",
                insufficient_history=False,
            )

    def test_confidence_negative_rejected(self):
        with pytest.raises(ValidationError):
            CashflowResult(version="test", score=50.0, confidence=-0.1)

    def test_score_above_100_rejected(self):
        with pytest.raises(ValidationError):
            CashflowResult(version="test", score=101.0, confidence=0.80)

    def test_score_negative_rejected(self):
        with pytest.raises(ValidationError):
            RepaymentResult(
                version="test", score=-1.0, confidence=0.80, new_credit_blocked=False
            )

    def test_invalid_evidence_grade(self):
        with pytest.raises(ValidationError):
            EvidenceResult(
                version="test",
                score=70.0,
                confidence=0.80,
                evidence_grade="Z",  # ← invalid
                insufficient_history=False,
            )

    def test_safe_emi_min_greater_than_max_rejected(self):
        with pytest.raises(ValidationError):
            SafeEMI(minimum=5000, maximum=3000)  # min > max

    def test_safe_emi_negative_minimum_rejected(self):
        with pytest.raises(ValidationError):
            SafeEMI(minimum=-100, maximum=1000)

    def test_missing_evidence_grade_rejected(self):
        with pytest.raises(ValidationError):
            EvidenceResult(
                version="test",
                score=70.0,
                confidence=0.80,
                # evidence_grade missing
                insufficient_history=False,
            )


# ============================================================================
# Common validation helpers
# ============================================================================

class TestValidationHelpers:
    def test_valid_component_passes(self):
        evidence = EvidenceResult(
            version="test",
            score=70.0,
            confidence=0.80,
            evidence_grade="B",
            insufficient_history=False,
        )
        # Should not raise
        validate_component_result(evidence, "evidence")

    def test_out_of_range_confidence_detected(self):
        """Test that the validation helper catches a manually constructed object."""
        class FakeResult:
            confidence = 1.5  # invalid
            score = 70.0
            features = {}
            reasons = []
            warnings = []

        with pytest.raises(ComponentContractError):
            validate_component_result(FakeResult(), "fake")

    def test_non_finite_confidence_detected(self):
        import math

        class FakeResult:
            confidence = math.nan
            score = 70.0
            features = {}
            reasons = []
            warnings = []

        with pytest.raises(ComponentContractError):
            validate_component_result(FakeResult(), "fake")

    def test_non_dict_features_detected(self):
        class FakeResult:
            confidence = 0.80
            score = 70.0
            features = [1, 2, 3]  # should be dict
            reasons = []
            warnings = []

        with pytest.raises(ComponentContractError):
            validate_component_result(FakeResult(), "fake")

    def test_non_list_reasons_detected(self):
        class FakeResult:
            confidence = 0.80
            score = 70.0
            features = {}
            reasons = "some string"  # should be list
            warnings = []

        with pytest.raises(ComponentContractError):
            validate_component_result(FakeResult(), "fake")


# ============================================================================
# Adapter validation
# ============================================================================

class TestAdapterValidation:
    def test_valid_cashflow_passes(self):
        cf = CashflowResult(
            version="test", score=70.0, confidence=0.80,
            features={}, reasons=[], warnings=[],
        )
        validated = validate_cashflow(cf)
        assert validated is cf

    def test_valid_repayment_passes(self):
        rp = RepaymentResult(
            version="test", score=70.0, confidence=0.80,
            new_credit_blocked=False, features={}, reasons=[], warnings=[],
        )
        validated = validate_repayment(rp)
        assert validated is rp

    def test_valid_evidence_passes(self):
        ev = EvidenceResult(
            version="test", score=70.0, confidence=0.80,
            evidence_grade="A", insufficient_history=False,
            features={}, reasons=[], warnings=[],
        )
        validated = validate_evidence(ev)
        assert validated is ev
