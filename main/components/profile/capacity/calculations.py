"""
capacity/calculations.py

Pure, deterministic affordability calculation functions.

Design principles:
  - Every function is side-effect-free.
  - No randomness; random seed 42 is only relevant to mock data generators.
  - No ML; all formulas are explicit and auditable with a calculator.
  - Calculations use full floating-point precision; rounding happens only at
    the presentation layer (final JSON output).
  - Division-by-zero and invalid inputs are handled explicitly.

Formula reference (from the FinMitra specification):
  monthly_surplus = conservative_inflow
                    − household_essentials
                    − business_essentials
                    − existing_obligations

  safe_emi_min = max(0, monthly_surplus × safe_emi_min_factor)
  safe_emi_max = max(0, monthly_surplus × safe_emi_max_factor)

  EMI = P × r × (1+r)^n / ((1+r)^n − 1)   [standard amortising formula]
  P   = EMI × ((1+r)^n − 1) / (r × (1+r)^n)  [inverse]

All monetary values in INR.  Rates as decimals (e.g. 0.12 for 12 % p.a.).
"""
from __future__ import annotations

import math

from typing import Dict, List, Optional

from common.schemas import (
    CapacityInput,
    CapacityPolicy,
    RequestedLoanAssessment,
    SafeEMI,
)


# ---------------------------------------------------------------------------
# Monthly surplus
# ---------------------------------------------------------------------------


def compute_monthly_surplus(inp: CapacityInput) -> float:
    """
    Calculate the conservative monthly surplus.

    surplus = inflow − household_essentials − business_essentials
              − formal_emis − informal_installments

    The requested new EMI is deliberately NOT subtracted here; the surplus
    represents the room available for new repayment obligations.
    """
    existing_obligations = (
        inp.existing_formal_emis + inp.existing_informal_installments
    )
    surplus = (
        inp.conservative_monthly_inflow
        - inp.essential_household_expense
        - inp.essential_business_expense
        - existing_obligations
    )
    return surplus


# ---------------------------------------------------------------------------
# Safe EMI
# ---------------------------------------------------------------------------


def compute_safe_emi(
    monthly_surplus: float,
    policy: CapacityPolicy,
) -> SafeEMI:
    """
    Derive the safe-EMI range from the monthly surplus and policy factors.

    Negative surplus → both bounds are ₹0 (never return negative affordability).
    """
    if monthly_surplus <= 0:
        return SafeEMI(minimum=0.0, maximum=0.0)

    safe_min = monthly_surplus * policy.safe_emi_min_factor
    safe_max = monthly_surplus * policy.safe_emi_max_factor
    return SafeEMI(minimum=max(0.0, safe_min), maximum=max(0.0, safe_max))


def zero_safe_emi() -> SafeEMI:
    """Return the blocked/zero safe-EMI object."""
    return SafeEMI(minimum=0.0, maximum=0.0)


# ---------------------------------------------------------------------------
# EMI calculation
# ---------------------------------------------------------------------------


def compute_emi(
    principal: float,
    annual_interest_rate: float,
    tenure_months: int,
) -> float:
    """
    Standard amortising EMI formula.

    EMI = P × r × (1+r)^n / ((1+r)^n − 1)

    where r = monthly_rate = annual_interest_rate / 12

    For zero-interest loans:
        EMI = P / n

    Args:
        principal          : Loan principal in INR; must be > 0.
        annual_interest_rate: Annual interest rate as a decimal (e.g. 0.12).
                             Must be ≥ 0.
        tenure_months      : Loan tenure in months; must be > 0.

    Returns:
        Monthly EMI in INR.

    Raises:
        ValueError: for invalid inputs.
    """
    if principal <= 0:
        raise ValueError(f"principal must be > 0; got {principal}")
    if annual_interest_rate < 0:
        raise ValueError(f"annual_interest_rate must be ≥ 0; got {annual_interest_rate}")
    if tenure_months <= 0:
        raise ValueError(f"tenure_months must be > 0; got {tenure_months}")

    if annual_interest_rate == 0:
        return principal / tenure_months

    r = annual_interest_rate / 12.0
    n = tenure_months
    factor = (1 + r) ** n
    emi = principal * r * factor / (factor - 1)
    return emi


# ---------------------------------------------------------------------------
# Maximum principal (inverse of EMI formula)
# ---------------------------------------------------------------------------


def compute_max_principal(
    safe_emi_max: float,
    annual_interest_rate: float,
    tenure_months: int,
) -> float:
    """
    Maximum affordable principal given the safe EMI maximum.

    P = EMI × ((1+r)^n − 1) / (r × (1+r)^n)

    For zero interest:
        P = EMI × n

    Args:
        safe_emi_max         : Safe EMI upper bound in INR.
        annual_interest_rate : Annual interest rate as a decimal.
        tenure_months        : Tenure in months.

    Returns:
        Maximum principal in INR (≥ 0).
    """
    if safe_emi_max <= 0:
        return 0.0
    if tenure_months <= 0:
        raise ValueError(f"tenure_months must be > 0; got {tenure_months}")
    if annual_interest_rate < 0:
        raise ValueError(f"annual_interest_rate must be ≥ 0; got {annual_interest_rate}")

    if annual_interest_rate == 0:
        return safe_emi_max * tenure_months

    r = annual_interest_rate / 12.0
    n = tenure_months
    factor = (1 + r) ** n
    principal = safe_emi_max * (factor - 1) / (r * factor)
    return principal


def compute_max_principal_table(
    safe_emi_max: float,
    annual_interest_rate: float,
    tenures: List[int],
) -> Dict[str, float]:
    """
    Build the max-principal table for multiple tenures.

    Returns a dict keyed as '<tenure>_months', e.g. {'6_months': 21000, ...}.
    Values are rounded to 2 decimal places for presentation but computed at
    full precision.
    """
    table: Dict[str, float] = {}
    for t in tenures:
        principal = compute_max_principal(safe_emi_max, annual_interest_rate, t)
        table[f"{t}_months"] = round(principal, 2)
    return table


# ---------------------------------------------------------------------------
# Requested-loan assessment
# ---------------------------------------------------------------------------


def assess_requested_loan(
    inp: CapacityInput,
    safe_emi: SafeEMI,
) -> Optional[RequestedLoanAssessment]:
    """
    Evaluate a specific loan request against the borrower's safe EMI.

    Returns None when the borrower has not provided loan parameters.
    """
    if (
        inp.requested_loan_amount is None
        or inp.annual_interest_rate is None
        or inp.tenure_months is None
    ):
        return None

    calculated_emi = compute_emi(
        principal=inp.requested_loan_amount,
        annual_interest_rate=inp.annual_interest_rate,
        tenure_months=inp.tenure_months,
    )
    within_capacity = (
        calculated_emi <= safe_emi.maximum
        or math.isclose(calculated_emi, safe_emi.maximum, rel_tol=1e-6, abs_tol=1e-4)
    )
    headroom = safe_emi.maximum - calculated_emi
    if abs(headroom) < 1e-6:
        headroom = 0.0

    return RequestedLoanAssessment(
        principal=inp.requested_loan_amount,
        annual_interest_rate=inp.annual_interest_rate,
        tenure_months=inp.tenure_months,
        calculated_emi=round(calculated_emi, 2),
        within_safe_capacity=within_capacity,
        emi_headroom=round(headroom, 2),
    )


# ---------------------------------------------------------------------------
# Capacity status
# ---------------------------------------------------------------------------


def determine_status(
    monthly_surplus: float,
    safe_emi_max: float,
    new_credit_blocked: bool,
    all_required_data_present: bool,
    policy: CapacityPolicy,
) -> str:
    """
    Determine the capacity status code deterministically.

    Priority order:
      1. INSUFFICIENT_DATA — required inputs missing.
      2. BLOCKED           — repayment engine has hard-blocked new credit.
      3. NO_CAPACITY       — zero surplus or zero safe EMI.
      4. LIMITED_CAPACITY  — positive but small safe EMI (< threshold).
      5. SUFFICIENT_CAPACITY — meaningful positive capacity.
    """
    if not all_required_data_present:
        return "INSUFFICIENT_DATA"
    if new_credit_blocked:
        return "BLOCKED"
    if monthly_surplus <= 0 or safe_emi_max <= 0:
        return "NO_CAPACITY"
    if safe_emi_max < policy.limited_capacity_threshold:
        return "LIMITED_CAPACITY"
    return "SUFFICIENT_CAPACITY"


# ---------------------------------------------------------------------------
# Confidence (input-completeness based)
# ---------------------------------------------------------------------------

# Weights used to derive confidence from data completeness.
# All weights must sum to 1.0.
_CONFIDENCE_WEIGHTS: Dict[str, float] = {
    "conservative_monthly_inflow": 0.20,
    "essential_household_expense": 0.15,
    "essential_business_expense": 0.15,
    "existing_formal_emis": 0.10,
    "existing_informal_installments": 0.10,
    "lowest_recent_monthly_inflow": 0.10,
    "available_balance_buffer": 0.05,
    "outstanding_delinquent_amount": 0.05,
    # Loan fields contribute jointly when all three are present.
    "loan_fields": 0.10,
}


def compute_confidence(inp: CapacityInput) -> float:
    """
    Compute a deterministic input-completeness confidence score in [0, 1].

    Confidence reflects how complete and reliable the affordability inputs are.
    It is NOT a statistical model confidence — it is a policy-defined measure
    of data coverage.

    Deductions:
      - Each missing / zero-when-zero-is-suspicious field reduces confidence.
      - Loan fields (all three) contribute jointly when fully provided.

    The CapacityInput Pydantic model ensures basic validity (no negatives,
    valid ratios). This function checks for completeness only.

    Note: conservative_monthly_inflow is required (gt=0) by the schema, so
    it always contributes its full weight when validation passes.
    """
    score = 0.0
    w = _CONFIDENCE_WEIGHTS

    # Required numeric fields — all validated by schema, always present
    score += w["conservative_monthly_inflow"]  # always present
    score += w["essential_household_expense"]
    score += w["essential_business_expense"]

    # Formal EMIs: 0.0 is a valid value (no obligations), so it always contributes
    score += w["existing_formal_emis"]

    # Informal installments: same reasoning
    score += w["existing_informal_installments"]

    # Lowest recent monthly inflow
    if inp.lowest_recent_monthly_inflow > 0:
        score += w["lowest_recent_monthly_inflow"]
    else:
        # Zero means no inflow data — partial credit (field exists but value suspicious)
        score += w["lowest_recent_monthly_inflow"] * 0.5

    # Available balance buffer — 0 is acceptable but reduces richness slightly
    score += w["available_balance_buffer"]

    # Delinquent amount — 0 is valid (no delinquency), contributes fully
    score += w["outstanding_delinquent_amount"]

    # Loan fields — all three must be present to get the weight
    if (
        inp.requested_loan_amount is not None
        and inp.annual_interest_rate is not None
        and inp.tenure_months is not None
    ):
        score += w["loan_fields"]
    # If not provided, it's optional — we don't penalise, just don't award the weight.
    # Rescale: without loan fields the total weight is 0.90, so normalise to 1.0.
    else:
        max_without_loan = 1.0 - w["loan_fields"]
        if max_without_loan > 0:
            score = score / max_without_loan

    # Clamp to [0, 1] for safety
    return max(0.0, min(1.0, score))
