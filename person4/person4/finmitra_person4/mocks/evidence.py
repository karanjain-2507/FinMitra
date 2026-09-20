"""
mocks/evidence.py

⚠️  MOCK ONLY — Not a real Evidence Engine implementation.

Provides deterministic mock EvidenceResult objects keyed by borrower scenario.
These satisfy the EvidenceResult contract and allow the Profile Assembler to
be tested without Person 1's real implementation.

When Person 1's Evidence Engine is ready, replace mock_evidence() calls in
the CLI and adapters with calls to the real engine.
"""
from __future__ import annotations

from common.reason_codes import ReasonCodes
from common.schemas import EvidenceResult, Reason

# -------------------------------------------------------------------------
# Mock scenario data
# -------------------------------------------------------------------------
# Each entry maps a scenario name to the keyword arguments for EvidenceResult.

_SCENARIOS: dict[str, dict] = {
    "strong_borrower": {
        "version": "mock-1.0",
        "score": 82.0,
        "confidence": 0.88,
        "evidence_grade": "A",
        "insufficient_history": False,
        "features": {
            "transaction_months_observed": 12,
            "data_completeness": 0.95,
            "anomaly_count": 0,
        },
        "reasons": [
            Reason(
                code=ReasonCodes.EV01.code,
                direction="POSITIVE",
                impact=None,
                message="12 months of consistent, complete transaction data. No anomalies detected.",
            )
        ],
        "warnings": [],
    },
    "seasonal_business": {
        "version": "mock-1.0",
        "score": 68.0,
        "confidence": 0.75,
        "evidence_grade": "B",
        "insufficient_history": False,
        "features": {
            "transaction_months_observed": 10,
            "data_completeness": 0.80,
            "anomaly_count": 1,
            "note": "Seasonal gaps detected — expected for agricultural borrower.",
        },
        "reasons": [
            Reason(
                code=ReasonCodes.EV02.code,
                direction="NEUTRAL",
                impact=None,
                message=(
                    "Transaction data shows seasonal patterns with periods of low "
                    "activity. Consistent with agricultural income cycle."
                ),
            )
        ],
        "warnings": [
            "SEASONAL_GAPS: Long gaps in transaction history detected. "
            "Consistent with seasonal business — not classified as suspicious."
        ],
    },
    "thin_file": {
        "version": "mock-1.0",
        "score": None,
        "confidence": 0.40,
        "evidence_grade": "D",
        "insufficient_history": True,
        "features": {
            "transaction_months_observed": 2,
            "data_completeness": 0.55,
            "anomaly_count": 0,
        },
        "reasons": [
            Reason(
                code=ReasonCodes.EV04.code,
                direction="NEGATIVE",
                impact=None,
                message=(
                    "Only 2 months of transaction history available. "
                    "Insufficient to establish reliable income or repayment patterns."
                ),
            )
        ],
        "warnings": [
            "THIN_FILE: Only 2 months of data. Readiness index will be set to None."
        ],
    },
    "unpaid_loan": {
        "version": "mock-1.0",
        "score": 55.0,
        "confidence": 0.82,
        "evidence_grade": "C",
        "insufficient_history": False,
        "features": {
            "transaction_months_observed": 9,
            "data_completeness": 0.88,
            "anomaly_count": 2,
            "note": "Irregular repayment transactions detected.",
        },
        "reasons": [
            Reason(
                code=ReasonCodes.EV03.code,
                direction="NEGATIVE",
                impact=None,
                message=(
                    "Transaction data shows evidence of irregular repayment behaviour "
                    "on an existing obligation."
                ),
            )
        ],
        "warnings": [
            "REPAYMENT_ANOMALY: Irregular repayment transactions detected in statement."
        ],
    },
}


def mock_evidence(scenario: str = "strong_borrower") -> EvidenceResult:
    """
    Return a deterministic mock EvidenceResult for the given scenario.

    Args:
        scenario: One of 'strong_borrower', 'seasonal_business', 'thin_file',
                  'unpaid_loan'.

    Returns:
        EvidenceResult satisfying the integration contract.

    Raises:
        KeyError: if the scenario is not recognised.
    """
    if scenario not in _SCENARIOS:
        raise KeyError(
            f"Unknown evidence scenario: {scenario!r}. "
            f"Available: {list(_SCENARIOS)}"
        )
    data = _SCENARIOS[scenario]
    return EvidenceResult(**data)
