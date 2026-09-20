"""
tests/test_fixtures.py

Tests that validate each of the four demo fixtures produces the correct
conceptual output as described in the FinMitra specification.
"""
from __future__ import annotations

import json
import pathlib
import pytest

from tests.test_integration import run_from_fixture

FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures"


class TestFixtureFiles:
    """Verify that all four fixture files exist and are valid JSON."""

    @pytest.mark.parametrize("fname", [
        "strong_borrower.json",
        "seasonal_business.json",
        "thin_file.json",
        "unpaid_loan.json",
    ])
    def test_fixture_exists(self, fname):
        assert (FIXTURES_DIR / fname).exists(), f"Missing fixture: {fname}"

    @pytest.mark.parametrize("fname", [
        "strong_borrower.json",
        "seasonal_business.json",
        "thin_file.json",
        "unpaid_loan.json",
    ])
    def test_fixture_is_valid_json(self, fname):
        with (FIXTURES_DIR / fname).open() as fh:
            data = json.load(fh)
        assert "capacity_input" in data

    @pytest.mark.parametrize("fname", [
        "strong_borrower.json",
        "seasonal_business.json",
        "thin_file.json",
        "unpaid_loan.json",
    ])
    def test_fixture_has_scenario(self, fname):
        with (FIXTURES_DIR / fname).open() as fh:
            data = json.load(fh)
        assert "scenario" in data


class TestFixtureExpectedBehavior:
    """Verify the expected conceptual outcomes per the specification."""

    def test_strong_borrower_sufficient_capacity(self):
        profile = run_from_fixture("strong_borrower.json")
        assert profile.capacity.status in ("SUFFICIENT_CAPACITY", "LIMITED_CAPACITY")
        assert profile.safe_emi.maximum > 2000
        assert profile.readiness_index is not None and profile.readiness_index > 50

    def test_seasonal_not_blocked(self):
        """Seasonal gaps should NOT auto-trigger a block."""
        profile = run_from_fixture("seasonal_business.json")
        assert profile.repayment.new_credit_blocked is False
        assert profile.capacity.status != "BLOCKED"
        assert profile.readiness_index is not None

    def test_thin_file_readiness_none(self):
        """Thin file must produce readiness_index = null."""
        profile = run_from_fixture("thin_file.json")
        assert profile.readiness_index is None

    def test_unpaid_loan_safe_emi_zero(self):
        """Hard block must result in ₹0 safe EMI."""
        profile = run_from_fixture("unpaid_loan.json")
        assert profile.safe_emi.minimum == 0.0
        assert profile.safe_emi.maximum == 0.0

    def test_unpaid_loan_readiness_at_most_35(self):
        profile = run_from_fixture("unpaid_loan.json")
        assert profile.readiness_index is not None
        assert profile.readiness_index <= 35.0

    def test_strong_borrower_requested_loan_assessed(self):
        """Strong borrower fixture includes a loan request — it should be assessed."""
        profile = run_from_fixture("strong_borrower.json")
        assert profile.capacity.requested_loan is not None
        assert profile.capacity.requested_loan.principal == 40000

    def test_seasonal_requested_loan_assessed(self):
        profile = run_from_fixture("seasonal_business.json")
        assert profile.capacity.requested_loan is not None

    def test_unpaid_loan_requested_loan_within_capacity_false(self):
        """When blocked, requested loan EMI should not be within capacity."""
        profile = run_from_fixture("unpaid_loan.json")
        if profile.capacity.requested_loan is not None:
            # When safe_emi_max = 0, any EMI > 0 exceeds capacity
            assert profile.capacity.requested_loan.within_safe_capacity is False

    def test_borrower_ids_match(self):
        """Borrower IDs from fixtures should flow through to the profile."""
        ids = {
            "strong_borrower.json": "B001",
            "seasonal_business.json": "B002",
            "thin_file.json": "B003",
            "unpaid_loan.json": "B004",
        }
        for fname, expected_id in ids.items():
            profile = run_from_fixture(fname)
            assert profile.borrower_id == expected_id, (
                f"{fname}: expected borrower_id={expected_id!r}, "
                f"got {profile.borrower_id!r}"
            )
