"""
capacity/stress_tests.py

Deterministic stress-test scenarios for the Capacity Engine.

Each stress test:
  1. Takes the canonical CapacityInput and policy.
  2. Constructs a modified scenario (without mutating the original).
  3. Re-runs the same pure calculation functions.
  4. Produces a StressTestResult with deterministic, calculation-backed reasons.

No randomness.  No ML.  Every number is traceable to the inputs.

Stress test catalogue (per FinMitra specification):
  ST1 — 20% income decline for three consecutive months.
  ST2 — One zero-income month.
  ST3 — 30% essential-expense increase.
  ST4 — Existing informal installment continues (baseline verification).
  ST5 — Seasonal low-income period (uses lowest_recent_monthly_inflow).
"""
from __future__ import annotations

from typing import List

from common.schemas import CapacityInput, CapacityPolicy, StressTestResult
from capacity.calculations import compute_monthly_surplus, compute_safe_emi


# ---------------------------------------------------------------------------
# Severity helper
# ---------------------------------------------------------------------------

def _severity(
    baseline_emi_max: float,
    stressed_emi_max: float,
) -> str:
    """
    Classify stress severity from the relative drop in safe_emi_max.

    Rules:
      - LOW    : stressed ≥ 75 % of baseline
      - MEDIUM : stressed ≥ 40 % of baseline
      - HIGH   : stressed < 40 % of baseline  (or baseline was zero)
    """
    if baseline_emi_max <= 0:
        return "HIGH"
    ratio = stressed_emi_max / baseline_emi_max
    if ratio >= 0.75:
        return "LOW"
    if ratio >= 0.40:
        return "MEDIUM"
    return "HIGH"


def _passes(baseline_emi_max: float, stressed_emi_max: float) -> bool:
    """
    A stress test passes when the borrower retains at least 40% of baseline
    safe EMI capacity under stress.  When the baseline is zero, the test
    trivially passes (no capacity to lose).
    """
    if baseline_emi_max <= 0:
        return True
    return (stressed_emi_max / baseline_emi_max) >= 0.40


# ---------------------------------------------------------------------------
# ST1 — 20% income decline
# ---------------------------------------------------------------------------


def stress_income_drop_20pct(
    inp: CapacityInput,
    policy: CapacityPolicy,
    baseline_surplus: float,
    baseline_safe_emi_max: float,
) -> StressTestResult:
    """
    ST1: Simulate income falling by 20 % for three consecutive months.

    Stressed inflow = original_inflow × income_stress_factor (default 0.80).
    All expenses and obligations remain unchanged.
    """
    stressed_inflow = inp.conservative_monthly_inflow * policy.income_stress_factor
    income_drop = inp.conservative_monthly_inflow - stressed_inflow

    # Build a modified input for the surplus calculation
    stressed_inp = inp.model_copy(
        update={"conservative_monthly_inflow": stressed_inflow}
    )
    stressed_surplus = compute_monthly_surplus(stressed_inp)
    stressed_emi = compute_safe_emi(stressed_surplus, policy)

    reasons: list[str] = [
        f"Income falls from ₹{inp.conservative_monthly_inflow:,.0f} to "
        f"₹{stressed_inflow:,.0f} (−₹{income_drop:,.0f} / "
        f"{(1 - policy.income_stress_factor)*100:.0f}% decline).",
        f"Stressed monthly surplus: ₹{stressed_surplus:,.0f} "
        f"(baseline: ₹{baseline_surplus:,.0f}).",
        f"Stressed safe EMI max: ₹{stressed_emi.maximum:,.0f} "
        f"(baseline: ₹{baseline_safe_emi_max:,.0f}).",
    ]
    if stressed_surplus < 0:
        reasons.append(
            "Stressed surplus is negative — borrower cannot cover essentials "
            "during an income decline of this magnitude."
        )

    return StressTestResult(
        name="income_drop_20pct",
        description=(
            f"Income falls {(1 - policy.income_stress_factor)*100:.0f}% "
            "for three consecutive months."
        ),
        baseline_monthly_surplus=round(baseline_surplus, 2),
        stressed_monthly_surplus=round(stressed_surplus, 2),
        baseline_safe_emi_max=round(baseline_safe_emi_max, 2),
        stressed_safe_emi_max=round(stressed_emi.maximum, 2),
        passed=_passes(baseline_safe_emi_max, stressed_emi.maximum),
        severity=_severity(baseline_safe_emi_max, stressed_emi.maximum),
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# ST2 — One zero-income month
# ---------------------------------------------------------------------------


def stress_zero_income_month(
    inp: CapacityInput,
    policy: CapacityPolicy,
    baseline_surplus: float,
    baseline_safe_emi_max: float,
) -> StressTestResult:
    """
    ST2: Simulate one month of zero income.

    The borrower's inflow drops to ₹0.  Essential expenses and obligations
    remain.  This tests whether the available_balance_buffer can absorb the
    shock without the borrower defaulting on existing obligations.
    """
    if not policy.zero_income_stress_enabled:
        return StressTestResult(
            name="zero_income_month",
            description="Zero-income month stress test (disabled by policy).",
            baseline_monthly_surplus=round(baseline_surplus, 2),
            stressed_monthly_surplus=round(baseline_surplus, 2),
            baseline_safe_emi_max=round(baseline_safe_emi_max, 2),
            stressed_safe_emi_max=round(baseline_safe_emi_max, 2),
            passed=True,
            severity="LOW",
            reasons=["Test disabled by policy configuration."],
        )

    # Surplus when income = 0
    stressed_inp = inp.model_copy(update={"conservative_monthly_inflow": 0.0})
    stressed_surplus = compute_monthly_surplus(stressed_inp)
    stressed_emi = compute_safe_emi(stressed_surplus, policy)

    # Deficit = negative surplus in zero-income month
    deficit = abs(min(0, stressed_surplus))
    buffer = inp.available_balance_buffer
    can_absorb = buffer >= deficit

    reasons: list[str] = [
        "Income drops to ₹0 for one month.",
        f"Monthly obligations (expenses + EMIs): ₹{deficit:,.0f}.",
        f"Available balance buffer: ₹{buffer:,.0f}.",
    ]
    if can_absorb:
        reasons.append(
            f"Buffer (₹{buffer:,.0f}) is sufficient to cover the one-month deficit "
            f"(₹{deficit:,.0f})."
        )
    else:
        reasons.append(
            f"Buffer (₹{buffer:,.0f}) is INSUFFICIENT to cover the one-month "
            f"deficit (₹{deficit:,.0f}). Shortfall: ₹{deficit - buffer:,.0f}."
        )

    # Pass criterion: buffer absorbs the deficit
    passed = can_absorb

    return StressTestResult(
        name="zero_income_month",
        description="Income drops to ₹0 for one month.",
        baseline_monthly_surplus=round(baseline_surplus, 2),
        stressed_monthly_surplus=round(stressed_surplus, 2),
        baseline_safe_emi_max=round(baseline_safe_emi_max, 2),
        stressed_safe_emi_max=round(stressed_emi.maximum, 2),
        passed=passed,
        severity="HIGH" if not can_absorb else "MEDIUM",
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# ST3 — 30% essential-expense increase
# ---------------------------------------------------------------------------


def stress_expense_increase_30pct(
    inp: CapacityInput,
    policy: CapacityPolicy,
    baseline_surplus: float,
    baseline_safe_emi_max: float,
) -> StressTestResult:
    """
    ST3: Essential household + business expenses rise by 30%.

    stressed_essentials = base_essentials × expense_stress_factor (default 1.30).
    Income and obligations remain unchanged.
    """
    base_essentials = (
        inp.essential_household_expense + inp.essential_business_expense
    )
    stressed_essentials = base_essentials * policy.expense_stress_factor
    extra_expense = stressed_essentials - base_essentials

    stressed_inp = inp.model_copy(
        update={
            "essential_household_expense": inp.essential_household_expense
            * policy.expense_stress_factor,
            "essential_business_expense": inp.essential_business_expense
            * policy.expense_stress_factor,
        }
    )
    stressed_surplus = compute_monthly_surplus(stressed_inp)
    stressed_emi = compute_safe_emi(stressed_surplus, policy)

    reasons: list[str] = [
        f"Essential expenses rise from ₹{base_essentials:,.0f} to "
        f"₹{stressed_essentials:,.0f} "
        f"(+₹{extra_expense:,.0f} / {(policy.expense_stress_factor - 1)*100:.0f}% increase).",
        f"Stressed monthly surplus: ₹{stressed_surplus:,.0f} "
        f"(baseline: ₹{baseline_surplus:,.0f}).",
        f"Stressed safe EMI max: ₹{stressed_emi.maximum:,.0f} "
        f"(baseline: ₹{baseline_safe_emi_max:,.0f}).",
    ]
    if stressed_surplus < 0:
        reasons.append(
            "Stressed surplus is negative — essential expenses exceed income "
            "under this scenario."
        )

    return StressTestResult(
        name="expense_increase_30pct",
        description=(
            f"Essential household and business expenses rise by "
            f"{(policy.expense_stress_factor - 1)*100:.0f}%."
        ),
        baseline_monthly_surplus=round(baseline_surplus, 2),
        stressed_monthly_surplus=round(stressed_surplus, 2),
        baseline_safe_emi_max=round(baseline_safe_emi_max, 2),
        stressed_safe_emi_max=round(stressed_emi.maximum, 2),
        passed=_passes(baseline_safe_emi_max, stressed_emi.maximum),
        severity=_severity(baseline_safe_emi_max, stressed_emi.maximum),
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# ST4 — Existing informal installment continues
# ---------------------------------------------------------------------------


def stress_existing_informal_continues(
    inp: CapacityInput,
    policy: CapacityPolicy,
    baseline_surplus: float,
    baseline_safe_emi_max: float,
) -> StressTestResult:
    """
    ST4: Verify that affordability is calculated AFTER existing informal
    obligations, not on gross income.

    This is the baseline calculation — it confirms that informal installments
    are NOT assumed to disappear when assessing new-credit capacity.

    The stressed surplus equals the baseline surplus (no new shock); the test
    passes when the surplus is positive after all obligations.
    """
    informal = inp.existing_informal_installments
    formal = inp.existing_formal_emis
    total_obligations = formal + informal

    reasons: list[str] = [
        f"Formal EMIs: ₹{formal:,.0f}/month.",
        f"Informal installments: ₹{informal:,.0f}/month.",
        f"Total existing obligations: ₹{total_obligations:,.0f}/month.",
        f"Monthly surplus after all obligations: ₹{baseline_surplus:,.0f}.",
    ]
    if informal > 0:
        reasons.append(
            f"Informal obligation (₹{informal:,.0f}) is retained in the "
            "calculation — it is not assumed to disappear."
        )
    else:
        reasons.append("No informal installments on record.")

    passed = baseline_surplus > 0

    return StressTestResult(
        name="informal_installment_continues",
        description=(
            "Confirms affordability is assessed after existing informal "
            "installments, not on gross income."
        ),
        baseline_monthly_surplus=round(baseline_surplus, 2),
        stressed_monthly_surplus=round(baseline_surplus, 2),
        baseline_safe_emi_max=round(baseline_safe_emi_max, 2),
        stressed_safe_emi_max=round(baseline_safe_emi_max, 2),
        passed=passed,
        severity="LOW" if passed else "HIGH",
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# ST5 — Seasonal low-income period
# ---------------------------------------------------------------------------


def stress_seasonal_low_income(
    inp: CapacityInput,
    policy: CapacityPolicy,
    baseline_surplus: float,
    baseline_safe_emi_max: float,
) -> StressTestResult:
    """
    ST5: Use the borrower's lowest recent monthly inflow as the income scenario.

    This test is specifically designed for seasonal businesses (farmers, traders)
    that have genuine low-income periods.  A long gap alone does NOT make the
    borrower high-risk; only the affordability during the low-income period
    matters for this test.

    Passes when the surplus during the low-income period is ≥ 0 (the borrower
    can at least cover essentials + obligations, even without additional EMI).
    """
    low_inflow = inp.lowest_recent_monthly_inflow
    stressed_inp = inp.model_copy(
        update={"conservative_monthly_inflow": low_inflow}
    )
    stressed_surplus = compute_monthly_surplus(stressed_inp)
    stressed_emi = compute_safe_emi(stressed_surplus, policy)

    inflow_drop = inp.conservative_monthly_inflow - low_inflow
    drop_pct = (
        inflow_drop / inp.conservative_monthly_inflow * 100
        if inp.conservative_monthly_inflow > 0
        else 0
    )

    reasons: list[str] = [
        f"Conservative inflow: ₹{inp.conservative_monthly_inflow:,.0f}/month.",
        f"Lowest recent monthly inflow: ₹{low_inflow:,.0f}/month "
        f"(−₹{inflow_drop:,.0f} / {drop_pct:.1f}% below conservative estimate).",
        f"Stressed surplus at lowest inflow: ₹{stressed_surplus:,.0f}.",
        f"Stressed safe EMI max: ₹{stressed_emi.maximum:,.0f}.",
    ]
    if stressed_surplus >= 0:
        reasons.append(
            "Borrower can cover existing obligations even during the "
            "low-income period — seasonal profile does not indicate inherent risk."
        )
    else:
        reasons.append(
            f"Surplus is negative (₹{stressed_surplus:,.0f}) during the low-income "
            "period — existing obligations exceed inflow at the seasonal trough."
        )

    # Pass: surplus ≥ 0 during the seasonal trough
    passed = stressed_surplus >= 0

    return StressTestResult(
        name="seasonal_low_income",
        description=(
            "Evaluates affordability using the borrower's lowest recent "
            "monthly inflow (seasonal trough scenario)."
        ),
        baseline_monthly_surplus=round(baseline_surplus, 2),
        stressed_monthly_surplus=round(stressed_surplus, 2),
        baseline_safe_emi_max=round(baseline_safe_emi_max, 2),
        stressed_safe_emi_max=round(stressed_emi.maximum, 2),
        passed=passed,
        severity=_severity(baseline_safe_emi_max, stressed_emi.maximum),
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# Run all stress tests
# ---------------------------------------------------------------------------


def run_all_stress_tests(
    inp: CapacityInput,
    policy: CapacityPolicy,
    baseline_surplus: float,
    baseline_safe_emi_max: float,
) -> List[StressTestResult]:
    """
    Execute all five stress tests and return their results.

    Tests are independent; they do not influence each other.
    """
    return [
        stress_income_drop_20pct(inp, policy, baseline_surplus, baseline_safe_emi_max),
        stress_zero_income_month(inp, policy, baseline_surplus, baseline_safe_emi_max),
        stress_expense_increase_30pct(inp, policy, baseline_surplus, baseline_safe_emi_max),
        stress_existing_informal_continues(inp, policy, baseline_surplus, baseline_safe_emi_max),
        stress_seasonal_low_income(inp, policy, baseline_surplus, baseline_safe_emi_max),
    ]
