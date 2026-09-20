"""
mocks/cashflow.py

⚠️  MOCK ONLY — Not a real Cash-Flow Model implementation.

Provides deterministic mock CashflowResult objects for integration testing.
cashflow.score contributes 55% to the readiness index in the Profile Assembler.

When Person 2's Cash-Flow Model is ready, replace mock_cashflow() calls with
real engine calls.  The Profile Assembler contract does not need to change.
"""
from __future__ import annotations

from common.reason_codes import ReasonCodes
from common.schemas import CashflowResult, Reason

_SCENARIOS: dict[str, dict] = {
    "strong_borrower": {
        "version": "mock-1.0",
        "score": 78.0,
        "confidence": 0.85,
        "features": {
            "average_monthly_inflow": 28000.0,
            "inflow_stability": 0.82,
            "outflow_ratio": 0.71,
        },
        "reasons": [
            Reason(
                code=ReasonCodes.CF01.code,
                direction="POSITIVE",
                impact=None,
                message=(
                    "Consistent monthly inflows with low variance. "
                    "Business expenses are well-controlled."
                ),
            )
        ],
        "warnings": [],
    },
    "seasonal_business": {
        "version": "mock-1.0",
        "score": 58.0,
        "confidence": 0.70,
        "features": {
            "average_monthly_inflow": 22000.0,
            "inflow_stability": 0.55,
            "outflow_ratio": 0.78,
            "seasonal_pattern_detected": True,
        },
        "reasons": [
            Reason(
                code=ReasonCodes.CF02.code,
                direction="NEUTRAL",
                impact=None,
                message=(
                    "Moderate cash-flow stability. Large seasonal variance observed "
                    "— typical for agricultural / harvest-cycle businesses. "
                    "Conservative inflow used for affordability."
                ),
            )
        ],
        "warnings": [
            "SEASONAL_INCOME: High variance in monthly inflows. "
            "Conservative estimate used."
        ],
    },
    "thin_file": {
        "version": "mock-1.0",
        "score": 45.0,
        "confidence": 0.42,
        "features": {
            "average_monthly_inflow": 15000.0,
            "inflow_stability": 0.50,
            "outflow_ratio": 0.82,
            "data_months": 2,
        },
        "reasons": [
            Reason(
                code=ReasonCodes.CF02.code,
                direction="NEGATIVE",
                impact=None,
                message=(
                    "Limited data (2 months) — cash-flow score has low confidence. "
                    "Cannot establish reliable income stability estimate."
                ),
            )
        ],
        "warnings": [
            "LOW_DATA: Only 2 months of cash-flow data. Score confidence is low."
        ],
    },
    "unpaid_loan": {
        "version": "mock-1.0",
        "score": 72.0,
        "confidence": 0.80,
        "features": {
            "average_monthly_inflow": 35000.0,
            "inflow_stability": 0.78,
            "outflow_ratio": 0.65,
        },
        "reasons": [
            Reason(
                code=ReasonCodes.CF01.code,
                direction="POSITIVE",
                impact=None,
                message=(
                    "Strong and stable monthly inflows. Business generates healthy "
                    "cash flow. Repayment failure is a willingness issue, not a "
                    "cash-flow issue."
                ),
            )
        ],
        "warnings": [],
    },
}


def mock_cashflow(scenario: str = "strong_borrower") -> CashflowResult:
    """
    Return a deterministic mock CashflowResult for the given scenario.

    Args:
        scenario: One of 'strong_borrower', 'seasonal_business', 'thin_file',
                  'unpaid_loan'.

    Returns:
        CashflowResult satisfying the integration contract.

    Raises:
        KeyError: if the scenario is not recognised.
    """
    if scenario not in _SCENARIOS:
        raise KeyError(
            f"Unknown cashflow scenario: {scenario!r}. "
            f"Available: {list(_SCENARIOS)}"
        )
    data = _SCENARIOS[scenario]
    return CashflowResult(**data)
