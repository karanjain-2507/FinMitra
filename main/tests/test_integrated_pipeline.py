from __future__ import annotations

import pytest

from finmitra.demo import build_demo
from finmitra.runner import assess
from finmitra.schemas import IntegratedBorrowerInput
from run_finmitra import render_summary


@pytest.fixture(scope="module")
def strong_result():
    return assess(IntegratedBorrowerInput.model_validate(build_demo("strong")))


@pytest.fixture(scope="module")
def unpaid_result():
    return assess(IntegratedBorrowerInput.model_validate(build_demo("unpaid")))


def test_real_engines_are_connected(strong_result):
    profile = strong_result["profile"]
    assert strong_result["lineage"]["normalized_transaction_count"] >= 80
    assert profile["evidence"]["version"] != "mock"
    assert profile["cashflow"]["score"] is not None
    assert 0 <= profile["cashflow"]["stress_probability"] <= 1
    assert profile["cashflow"]["score"] == pytest.approx(
        100 * (1 - profile["cashflow"]["stress_probability"]), abs=0.001
    )
    assert profile["readiness_index"] is not None
    assert profile["safe_emi"]["maximum"] > 0


def test_paise_is_converted_to_inr(strong_result):
    cashflow = strong_result["profile"]["cashflow"]["features"]
    capacity = strong_result["profile"]["capacity"]["features"]
    assert capacity["conservative_monthly_inflow"] == pytest.approx(
        cashflow["conservative_monthly_inflow_paise"] / 100.0
    )


def test_unpaid_loan_overrides_strong_cashflow(strong_result, unpaid_result):
    strong = strong_result["profile"]
    unpaid = unpaid_result["profile"]
    assert unpaid["cashflow"]["score"] == strong["cashflow"]["score"]
    assert unpaid["repayment"]["new_credit_blocked"] is True
    assert unpaid["repayment"]["status"] == "SEVERELY_UNPAID"
    assert unpaid["readiness_index"] <= 35
    assert unpaid["safe_emi"] == {"minimum": 0.0, "maximum": 0.0}


def test_cli_summary_surfaces_the_decision(unpaid_result):
    summary = render_summary(unpaid_result)
    assert "Cash-flow stress:" in summary
    assert "Repayment status:     SEVERELY_UNPAID" in summary
    assert "Credit blocked:       YES" in summary
    assert "Safe EMI:             ₹0 – ₹0" in summary
    assert "BLOCKED" in summary


def test_thin_history_returns_unknown_not_fake_strength():
    result = assess(IntegratedBorrowerInput.model_validate(build_demo("thin")))
    profile = result["profile"]
    assert profile["cashflow"]["score"] is None
    assert profile["readiness_index"] is None
    assert any("INSUFFICIENT" in flag for flag in profile["policy_flags"])
