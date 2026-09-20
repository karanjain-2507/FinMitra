"""
tests/test_integration.py

End-to-end integration tests: Input fixture → Mock components → Capacity Engine
→ Profile Assembler → Final JSON.

These tests validate the complete pipeline for all four demo scenarios.
"""
from __future__ import annotations

import json
import pathlib
import pytest

from capacity.engine import CapacityEngine
from common.schemas import CapacityInput
from fusion.profile_assembler import ProfileAssembler
from mocks.cashflow import mock_cashflow
from mocks.evidence import mock_evidence
from mocks.repayment import mock_repayment


FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Helper: run pipeline from fixture file
# ---------------------------------------------------------------------------

def run_from_fixture(fixture_name: str):
    """Load a fixture JSON and run the full pipeline. Returns the profile."""
    fixture_path = FIXTURES_DIR / fixture_name
    with fixture_path.open() as fh:
        data = json.load(fh)

    scenario = data.get("scenario", "strong_borrower")
    borrower_id = data.get("borrower_id")
    capacity_input = CapacityInput.model_validate(data["capacity_input"])

    evidence = mock_evidence(scenario)
    cashflow = mock_cashflow(scenario)
    repayment = mock_repayment(scenario)

    capacity = CapacityEngine.assess(
        inp=capacity_input,
        new_credit_blocked=repayment.new_credit_blocked,
    )

    return ProfileAssembler.assemble(
        evidence=evidence,
        cashflow=cashflow,
        repayment=repayment,
        capacity=capacity,
        borrower_id=borrower_id,
    )


# ============================================================================
# Scenario: Strong Borrower
# ============================================================================

class TestStrongBorrowerIntegration:
    def test_pipeline_runs(self):
        profile = run_from_fixture("strong_borrower.json")
        assert profile is not None

    def test_profile_version(self):
        profile = run_from_fixture("strong_borrower.json")
        assert profile.profile_version == "1.0"

    def test_readiness_index_positive(self):
        profile = run_from_fixture("strong_borrower.json")
        assert profile.readiness_index is not None
        assert profile.readiness_index > 50

    def test_safe_emi_positive(self):
        profile = run_from_fixture("strong_borrower.json")
        assert profile.safe_emi.maximum > 0

    def test_capacity_status_sufficient(self):
        profile = run_from_fixture("strong_borrower.json")
        assert profile.capacity.status in ("SUFFICIENT_CAPACITY", "LIMITED_CAPACITY")

    def test_not_blocked(self):
        profile = run_from_fixture("strong_borrower.json")
        assert profile.repayment.new_credit_blocked is False
        assert profile.capacity.status != "BLOCKED"

    def test_confidence_in_range(self):
        profile = run_from_fixture("strong_borrower.json")
        assert 0.0 <= profile.overall_confidence <= 1.0

    def test_json_serializable(self):
        profile = run_from_fixture("strong_borrower.json")
        json_str = json.dumps(profile.model_dump(mode="json"))
        assert len(json_str) > 100

    def test_reasons_present(self):
        profile = run_from_fixture("strong_borrower.json")
        assert len(profile.final_reasons) > 0

    def test_no_nan_in_json(self):
        profile = run_from_fixture("strong_borrower.json")
        json_str = json.dumps(profile.model_dump(mode="json"))
        assert "NaN" not in json_str
        assert "Infinity" not in json_str


# ============================================================================
# Scenario: Seasonal Business
# ============================================================================

class TestSeasonalBusinessIntegration:
    def test_pipeline_runs(self):
        profile = run_from_fixture("seasonal_business.json")
        assert profile is not None

    def test_readiness_index_not_none(self):
        """Seasonal borrower should have a readiness index (not thin file)."""
        profile = run_from_fixture("seasonal_business.json")
        assert profile.readiness_index is not None

    def test_not_blocked(self):
        profile = run_from_fixture("seasonal_business.json")
        assert profile.repayment.new_credit_blocked is False

    def test_seasonal_stress_test_present(self):
        profile = run_from_fixture("seasonal_business.json")
        stress_names = [st.name for st in profile.capacity.stress_tests]
        assert "seasonal_low_income" in stress_names

    def test_capacity_score_is_none(self):
        profile = run_from_fixture("seasonal_business.json")
        assert profile.capacity.score is None

    def test_capacity_has_max_principal(self):
        profile = run_from_fixture("seasonal_business.json")
        assert "6_months" in profile.capacity.max_principal
        assert "12_months" in profile.capacity.max_principal
        assert "18_months" in profile.capacity.max_principal


# ============================================================================
# Scenario: Thin File
# ============================================================================

class TestThinFileIntegration:
    def test_pipeline_runs(self):
        profile = run_from_fixture("thin_file.json")
        assert profile is not None

    def test_readiness_index_is_none(self):
        """Thin file → insufficient_history → readiness_index must be None."""
        profile = run_from_fixture("thin_file.json")
        assert profile.readiness_index is None

    def test_insufficient_history_flag(self):
        profile = run_from_fixture("thin_file.json")
        history_flags = [f for f in profile.policy_flags if "INSUFFICIENT_HISTORY" in f]
        assert len(history_flags) >= 1

    def test_not_blocked(self):
        profile = run_from_fixture("thin_file.json")
        assert profile.repayment.new_credit_blocked is False

    def test_overall_confidence_is_lower(self):
        """Thin file should have lower confidence than strong borrower."""
        thin = run_from_fixture("thin_file.json")
        strong = run_from_fixture("strong_borrower.json")
        assert thin.overall_confidence < strong.overall_confidence


# ============================================================================
# Scenario: Unpaid Loan (Hard Block)
# ============================================================================

class TestUnpaidLoanIntegration:
    def test_pipeline_runs(self):
        profile = run_from_fixture("unpaid_loan.json")
        assert profile is not None

    def test_safe_emi_is_zero(self):
        """Hard block must force safe EMI to ₹0."""
        profile = run_from_fixture("unpaid_loan.json")
        assert profile.safe_emi.minimum == 0.0
        assert profile.safe_emi.maximum == 0.0

    def test_capacity_status_blocked(self):
        profile = run_from_fixture("unpaid_loan.json")
        assert profile.capacity.status == "BLOCKED"

    def test_readiness_capped_at_35(self):
        profile = run_from_fixture("unpaid_loan.json")
        assert profile.readiness_index is not None
        assert profile.readiness_index <= 35.0

    def test_block_policy_flag_present(self):
        profile = run_from_fixture("unpaid_loan.json")
        block_flags = [f for f in profile.policy_flags if "REPAYMENT_BLOCK_CEILING" in f]
        assert len(block_flags) >= 1

    def test_max_principal_is_zero(self):
        profile = run_from_fixture("unpaid_loan.json")
        for key, val in profile.capacity.max_principal.items():
            assert val == 0.0, f"max_principal[{key}] should be 0 when blocked"

    def test_capacity_reason_cp04_present(self):
        profile = run_from_fixture("unpaid_loan.json")
        codes = [r.code for r in profile.capacity.reasons]
        assert "CP04" in codes

    def test_delinquent_warning_present(self):
        profile = run_from_fixture("unpaid_loan.json")
        all_warnings = " ".join(profile.final_warnings)
        assert "25000" in all_warnings or "delinquent" in all_warnings.lower() or "DELINQUENCY" in all_warnings


# ============================================================================
# Cross-scenario checks
# ============================================================================

class TestCrossScenario:
    @pytest.mark.parametrize("fixture", [
        "strong_borrower.json",
        "seasonal_business.json",
        "thin_file.json",
        "unpaid_loan.json",
    ])
    def test_all_fixtures_produce_valid_json(self, fixture):
        profile = run_from_fixture(fixture)
        json_str = json.dumps(profile.model_dump(mode="json"))
        parsed = json.loads(json_str)
        assert "profile_version" in parsed
        assert "readiness_index" in parsed
        assert "overall_confidence" in parsed
        assert "safe_emi" in parsed
        assert "capacity" in parsed

    @pytest.mark.parametrize("fixture", [
        "strong_borrower.json",
        "seasonal_business.json",
        "thin_file.json",
        "unpaid_loan.json",
    ])
    def test_capacity_score_is_always_none(self, fixture):
        profile = run_from_fixture(fixture)
        assert profile.capacity.score is None

    @pytest.mark.parametrize("fixture", [
        "strong_borrower.json",
        "seasonal_business.json",
        "thin_file.json",
        "unpaid_loan.json",
    ])
    def test_five_stress_tests_always_present(self, fixture):
        profile = run_from_fixture(fixture)
        assert len(profile.capacity.stress_tests) == 5

    @pytest.mark.parametrize("fixture", [
        "strong_borrower.json",
        "seasonal_business.json",
        "thin_file.json",
        "unpaid_loan.json",
    ])
    def test_safe_emi_non_negative(self, fixture):
        profile = run_from_fixture(fixture)
        assert profile.safe_emi.minimum >= 0
        assert profile.safe_emi.maximum >= 0
