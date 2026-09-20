"""
capacity/engine.py

The Capacity Engine — the primary entry point for Person 4's affordability
assessment.

CapacityEngine.assess() orchestrates:
  1. Input validation (delegated to Pydantic + common.validation).
  2. Core calculations (capacity.calculations).
  3. Policy application (CapacityPolicy, hard blocks).
  4. Stress tests (capacity.stress_tests).
  5. Reason and warning generation.
  6. CapacityResult assembly.

Design rules:
  - Deterministic: same inputs → same output, always.
  - No ML, no LLM, no randomness.
  - All monetary outputs in INR (floats).
  - score is always None (capacity produces amounts, not a credit score).
  - Every decision is traceable to an input value and a named policy rule.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from common.reason_codes import ReasonCodes
from common.schemas import (
    CapacityInput,
    CapacityPolicy,
    CapacityResult,
    Reason,
    SafeEMI,
    StressTestResult,
)
from capacity.calculations import (
    assess_requested_loan,
    compute_confidence,
    compute_max_principal_table,
    compute_monthly_surplus,
    compute_safe_emi,
    determine_status,
    zero_safe_emi,
)
from capacity.stress_tests import run_all_stress_tests


class CapacityEngine:
    """
    Deterministic affordability engine.

    Usage::

        from capacity.engine import CapacityEngine
        from common.config import DEFAULT_POLICY
        from common.schemas import CapacityInput

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
        result = CapacityEngine.assess(inp, new_credit_blocked=False)
    """

    # Engine version — bump when calculation logic changes.
    VERSION: str = "1.0"

    @classmethod
    def assess(
        cls,
        inp: CapacityInput,
        new_credit_blocked: bool = False,
        policy: Optional[CapacityPolicy] = None,
    ) -> CapacityResult:
        """
        Run the full affordability assessment.

        Args:
            inp               : Validated CapacityInput.
            new_credit_blocked: Hard-block flag from the Repayment Engine.
                                When True, safe_emi is forced to ₹0.
            policy            : CapacityPolicy to use. Defaults to DEFAULT_POLICY.

        Returns:
            CapacityResult with all affordability information.
        """
        from common.config import DEFAULT_POLICY

        if policy is None:
            policy = DEFAULT_POLICY

        reasons: List[Reason] = []
        warnings: List[str] = []

        # ------------------------------------------------------------------
        # Step 1 — Core calculations
        # ------------------------------------------------------------------
        monthly_surplus = compute_monthly_surplus(inp)
        raw_safe_emi = compute_safe_emi(monthly_surplus, policy)

        # ------------------------------------------------------------------
        # Step 2 — Hard repayment block
        # ------------------------------------------------------------------
        if new_credit_blocked:
            safe_emi = zero_safe_emi()
            reasons.append(
                Reason(
                    code=ReasonCodes.CP04.code,
                    direction="NEGATIVE",
                    impact=None,
                    message=(
                        "New credit has been explicitly blocked by the Repayment "
                        "Engine due to unresolved delinquency. Safe EMI is set to "
                        "₹0 regardless of income or surplus."
                    ),
                )
            )
            warnings.append(
                "REPAYMENT_HARD_BLOCK: new_credit_blocked=True. "
                "Safe EMI forced to ₹0."
            )
        else:
            safe_emi = raw_safe_emi

        # ------------------------------------------------------------------
        # Step 3 — Interest rate for max-principal table
        # ------------------------------------------------------------------
        interest_rate_for_table = (
            inp.annual_interest_rate
            if inp.annual_interest_rate is not None
            else policy.default_annual_interest_rate
        )

        # ------------------------------------------------------------------
        # Step 4 — Max principal table
        # ------------------------------------------------------------------
        max_principal = compute_max_principal_table(
            safe_emi_max=safe_emi.maximum,
            annual_interest_rate=interest_rate_for_table,
            tenures=policy.max_principal_tenures,
        )

        # ------------------------------------------------------------------
        # Step 5 — Requested loan assessment
        # ------------------------------------------------------------------
        requested_loan = assess_requested_loan(inp, safe_emi)

        # ------------------------------------------------------------------
        # Step 6 — Stress tests
        # ------------------------------------------------------------------
        stress_tests = run_all_stress_tests(
            inp=inp,
            policy=policy,
            baseline_surplus=monthly_surplus,
            baseline_safe_emi_max=raw_safe_emi.maximum,  # use pre-block EMI for stress
        )

        # ------------------------------------------------------------------
        # Step 7 — Confidence
        # ------------------------------------------------------------------
        confidence = compute_confidence(inp)

        # ------------------------------------------------------------------
        # Step 8 — Status
        # ------------------------------------------------------------------
        status = determine_status(
            monthly_surplus=monthly_surplus,
            safe_emi_max=safe_emi.maximum,
            new_credit_blocked=new_credit_blocked,
            all_required_data_present=True,  # schema validation guarantees this
            policy=policy,
        )

        # ------------------------------------------------------------------
        # Step 9 — Reasons
        # ------------------------------------------------------------------
        reasons.extend(
            cls._build_reasons(
                inp=inp,
                monthly_surplus=monthly_surplus,
                safe_emi=safe_emi,
                new_credit_blocked=new_credit_blocked,
                requested_loan_assessment=requested_loan,
                stress_tests_failed=[st for st in stress_tests if not st.passed],
                policy=policy,
            )
        )

        # ------------------------------------------------------------------
        # Step 10 — Warnings
        # ------------------------------------------------------------------
        warnings.extend(
            cls._build_warnings(
                inp=inp,
                monthly_surplus=monthly_surplus,
                new_credit_blocked=new_credit_blocked,
                stress_tests=stress_tests,
            )
        )

        # ------------------------------------------------------------------
        # Step 11 — Features (explainability snapshot)
        # ------------------------------------------------------------------
        existing_obligations = (
            inp.existing_formal_emis + inp.existing_informal_installments
        )
        features: dict = {
            "conservative_monthly_inflow": inp.conservative_monthly_inflow,
            "essential_household_expense": inp.essential_household_expense,
            "essential_business_expense": inp.essential_business_expense,
            "existing_formal_emis": inp.existing_formal_emis,
            "existing_informal_installments": inp.existing_informal_installments,
            "total_existing_obligations": round(existing_obligations, 2),
            "income_volatility": inp.income_volatility,
            "lowest_recent_monthly_inflow": inp.lowest_recent_monthly_inflow,
            "available_balance_buffer": inp.available_balance_buffer,
            "outstanding_delinquent_amount": inp.outstanding_delinquent_amount,
            "monthly_surplus": round(monthly_surplus, 2),
            "safe_emi_min_factor": policy.safe_emi_min_factor,
            "safe_emi_max_factor": policy.safe_emi_max_factor,
            "new_credit_blocked": new_credit_blocked,
            "stress_tests_passed": sum(1 for st in stress_tests if st.passed),
            "stress_tests_total": len(stress_tests),
        }

        # ------------------------------------------------------------------
        # Assemble result
        # ------------------------------------------------------------------
        return CapacityResult(
            component="capacity",
            version=cls.VERSION,
            score=None,
            status=status,
            confidence=round(confidence, 4),
            features=features,
            safe_emi=safe_emi,
            max_principal=max_principal,
            requested_loan=requested_loan,
            stress_tests=stress_tests,
            reasons=reasons,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_reasons(
        inp: CapacityInput,
        monthly_surplus: float,
        safe_emi: SafeEMI,
        new_credit_blocked: bool,
        requested_loan_assessment,
        stress_tests_failed: List[StressTestResult],
        policy: CapacityPolicy,
    ) -> List[Reason]:
        reasons: List[Reason] = []

        if new_credit_blocked:
            # Already added above; don't duplicate.
            pass
        elif monthly_surplus > 0:
            obligations = (
                inp.existing_formal_emis + inp.existing_informal_installments
            )
            obligation_ratio = (
                obligations / inp.conservative_monthly_inflow
                if inp.conservative_monthly_inflow > 0 else 0
            )

            if safe_emi.maximum >= policy.limited_capacity_threshold:
                reasons.append(
                    Reason(
                        code=ReasonCodes.CP11.code,
                        direction="POSITIVE",
                        impact=round(monthly_surplus, 2),
                        message=(
                            f"Monthly surplus of ₹{monthly_surplus:,.0f} provides "
                            f"meaningful repayment headroom. "
                            f"Safe EMI range: ₹{safe_emi.minimum:,.0f}–"
                            f"₹{safe_emi.maximum:,.0f}."
                        ),
                    )
                )
            else:
                reasons.append(
                    Reason(
                        code=ReasonCodes.CP02.code,
                        direction="NEGATIVE",
                        impact=round(monthly_surplus, 2),
                        message=(
                            f"Monthly surplus of ₹{monthly_surplus:,.0f} is positive "
                            f"but limited. Safe EMI max: ₹{safe_emi.maximum:,.0f}."
                        ),
                    )
                )

            if obligation_ratio > 0.40:
                reasons.append(
                    Reason(
                        code=ReasonCodes.CP03.code,
                        direction="NEGATIVE",
                        impact=None,
                        message=(
                            f"Existing obligations (₹{obligations:,.0f}) represent "
                            f"{obligation_ratio*100:.1f}% of monthly inflow — "
                            "this constrains new repayment capacity."
                        ),
                    )
                )
        else:
            reasons.append(
                Reason(
                    code=ReasonCodes.CP10.code,
                    direction="NEGATIVE",
                    impact=round(monthly_surplus, 2),
                    message=(
                        f"Monthly surplus is ₹{monthly_surplus:,.0f} — expenses and "
                        "obligations exceed income. No additional repayment capacity."
                    ),
                )
            )

        # Outstanding delinquency warning
        if inp.outstanding_delinquent_amount > 0:
            reasons.append(
                Reason(
                    code=ReasonCodes.CP07.code,
                    direction="NEGATIVE",
                    impact=None,
                    message=(
                        f"Outstanding delinquent amount: "
                        f"₹{inp.outstanding_delinquent_amount:,.0f}. "
                        "This is surfaced for underwriter review; the hard-block "
                        "decision is owned by the Repayment Engine."
                    ),
                )
            )

        # Income volatility context
        if inp.income_volatility > 0.25:
            reasons.append(
                Reason(
                    code=ReasonCodes.CP12.code,
                    direction="NEGATIVE",
                    impact=None,
                    message=(
                        f"Income volatility is {inp.income_volatility:.2f} — "
                        "elevated volatility makes stress tests particularly relevant."
                    ),
                )
            )

        # Requested loan assessment
        if requested_loan_assessment is not None:
            if requested_loan_assessment.within_safe_capacity:
                reasons.append(
                    Reason(
                        code=ReasonCodes.CP08.code,
                        direction="POSITIVE",
                        impact=round(requested_loan_assessment.emi_headroom, 2),
                        message=(
                            f"Requested loan EMI of ₹{requested_loan_assessment.calculated_emi:,.0f} "
                            f"is within safe capacity (max ₹{safe_emi.maximum:,.0f}). "
                            f"Headroom: ₹{requested_loan_assessment.emi_headroom:,.0f}."
                        ),
                    )
                )
            else:
                reasons.append(
                    Reason(
                        code=ReasonCodes.CP09.code,
                        direction="NEGATIVE",
                        impact=round(requested_loan_assessment.emi_headroom, 2),
                        message=(
                            f"Requested loan EMI of ₹{requested_loan_assessment.calculated_emi:,.0f} "
                            f"EXCEEDS safe capacity (max ₹{safe_emi.maximum:,.0f}). "
                            f"Overrun: ₹{abs(requested_loan_assessment.emi_headroom):,.0f}."
                        ),
                    )
                )

        # Stress test failures
        if stress_tests_failed:
            reasons.append(
                Reason(
                    code=ReasonCodes.CP05.code,
                    direction="NEGATIVE",
                    impact=None,
                    message=(
                        f"{len(stress_tests_failed)} stress test(s) failed: "
                        + ", ".join(st.name for st in stress_tests_failed)
                        + ". Affordability may not be resilient under adverse conditions."
                    ),
                )
            )

        return reasons

    @staticmethod
    def _build_warnings(
        inp: CapacityInput,
        monthly_surplus: float,
        new_credit_blocked: bool,
        stress_tests: List[StressTestResult],
    ) -> List[str]:
        warnings: List[str] = []

        if inp.outstanding_delinquent_amount > 0:
            warnings.append(
                f"DELINQUENCY: Outstanding delinquent amount of "
                f"₹{inp.outstanding_delinquent_amount:,.0f} on record."
            )

        if monthly_surplus < 0:
            warnings.append(
                f"NEGATIVE_SURPLUS: Monthly expenses and obligations exceed income "
                f"by ₹{abs(monthly_surplus):,.0f}."
            )

        high_severity_failures = [
            st for st in stress_tests
            if not st.passed and st.severity == "HIGH"
        ]
        if high_severity_failures:
            warnings.append(
                f"HIGH_SEVERITY_STRESS: {len(high_severity_failures)} stress "
                f"test(s) with HIGH severity failed: "
                + ", ".join(st.name for st in high_severity_failures)
            )

        if inp.income_volatility > 0.30:
            warnings.append(
                f"HIGH_INCOME_VOLATILITY: Income volatility of "
                f"{inp.income_volatility:.2f} is high — income may be "
                "unreliable month-to-month."
            )

        return warnings
