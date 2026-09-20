"""
mocks/repayment.py

⚠️  MOCK ONLY — Not a real Repayment Engine implementation.

Provides deterministic mock RepaymentResult objects.
repayment.score contributes 45% to the readiness index.
repayment.new_credit_blocked triggers the hard-block policy in both the
Capacity Engine and the Profile Assembler.

When Person 3's Repayment Engine is ready, replace mock_repayment() calls.
No changes are needed in the Capacity Engine or Profile Assembler.
"""
from __future__ import annotations

from common.reason_codes import ReasonCodes
from common.schemas import Reason, RepaymentResult

_SCENARIOS: dict[str, dict] = {
    "strong_borrower": {
        "version": "mock-1.0",
        "score": 85.0,
        "confidence": 0.90,
        "new_credit_blocked": False,
        "features": {
            "loans_observed": 1,
            "on_time_payments_pct": 0.96,
            "overdue_amount": 0.0,
            "completed_loans": 1,
        },
        "reasons": [
            Reason(
                code=ReasonCodes.RP01.code,
                direction="POSITIVE",
                impact=None,
                message=(
                    "Borrower has completed one supplier loan with 96% on-time "
                    "payments. Strong repayment history."
                ),
            )
        ],
        "warnings": [],
    },
    "seasonal_business": {
        "version": "mock-1.0",
        "score": 65.0,
        "confidence": 0.72,
        "new_credit_blocked": False,
        "features": {
            "loans_observed": 1,
            "on_time_payments_pct": 0.78,
            "overdue_amount": 0.0,
            "notes": "Seasonal delays observed — payments made after harvest.",
        },
        "reasons": [
            Reason(
                code=ReasonCodes.RP02.code,
                direction="NEUTRAL",
                impact=None,
                message=(
                    "Partial history with seasonal payment delays. No overdue amounts. "
                    "Delays are consistent with harvest-cycle income patterns."
                ),
            )
        ],
        "warnings": [
            "SEASONAL_DELAYS: Payment delays observed during low-income periods. "
            "No defaults recorded."
        ],
    },
    "thin_file": {
        "version": "mock-1.0",
        "score": 50.0,
        "confidence": 0.38,
        "new_credit_blocked": False,
        "features": {
            "loans_observed": 0,
            "on_time_payments_pct": None,
            "overdue_amount": 0.0,
            "note": "No formal credit history found.",
        },
        "reasons": [
            Reason(
                code=ReasonCodes.RP02.code,
                direction="NEUTRAL",
                impact=None,
                message=(
                    "No formal repayment history found. Score is at the neutral "
                    "midpoint. Cannot confirm or deny repayment behaviour."
                ),
            )
        ],
        "warnings": [
            "NO_REPAYMENT_HISTORY: No formal loan repayment data available."
        ],
    },
    "unpaid_loan": {
        "version": "mock-1.0",
        "score": 20.0,
        "confidence": 0.88,
        "new_credit_blocked": True,
        "features": {
            "loans_observed": 1,
            "on_time_payments_pct": 0.0,
            "overdue_amount": 25000.0,
            "delinquent_days": 180,
            "note": "Borrower has an overdue informal supplier loan with zero repayments.",
        },
        "reasons": [
            Reason(
                code=ReasonCodes.RP03.code,
                direction="NEGATIVE",
                impact=None,
                message=(
                    "Active delinquency: ₹25,000 overdue on an informal supplier loan "
                    "with zero repayments made. New credit is blocked."
                ),
            )
        ],
        "warnings": [
            "NEW_CREDIT_BLOCKED: Active delinquency detected. "
            "new_credit_blocked=True. Safe EMI will be forced to ₹0."
        ],
    },
}


def mock_repayment(scenario: str = "strong_borrower") -> RepaymentResult:
    """
    Return a deterministic mock RepaymentResult for the given scenario.

    Args:
        scenario: One of 'strong_borrower', 'seasonal_business', 'thin_file',
                  'unpaid_loan'.

    Returns:
        RepaymentResult satisfying the integration contract.

    Raises:
        KeyError: if the scenario is not recognised.
    """
    if scenario not in _SCENARIOS:
        raise KeyError(
            f"Unknown repayment scenario: {scenario!r}. "
            f"Available: {list(_SCENARIOS)}"
        )
    data = _SCENARIOS[scenario]
    return RepaymentResult(**data)
