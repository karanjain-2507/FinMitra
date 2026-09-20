"""Deterministic backward-planning engine for FinMitra goals."""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING

from .calculations import (
    compute_emi,
    compute_max_principal,
    first_affordable_tenure,
    money,
)
from .schemas import (
    CurrentState,
    FinancialBaseline,
    FinancialGap,
    Goal,
    GoalSnapshot,
    LoanReadinessGoal,
    PlanAssumption,
    PlanPath,
    RequiredState,
    SafetySummary,
    SavingsTargetGoal,
    WhatIfResult,
)


ZERO = Decimal("0.00")


class WhatIfEngine:
    VERSION = "1.0"

    @classmethod
    def plan(cls, baseline: FinancialBaseline, goal: Goal) -> WhatIfResult:
        if isinstance(goal, LoanReadinessGoal):
            return cls._loan_plan(baseline, goal)
        if isinstance(goal, SavingsTargetGoal):
            return cls._savings_plan(baseline, goal)
        raise TypeError(f"Unsupported goal type: {type(goal)!r}")

    @staticmethod
    def _current_state(
        baseline: FinancialBaseline, *, reliable_cashflow: bool = True
    ) -> CurrentState:
        monthly_expenses = money(baseline.household_expense + baseline.business_expense)
        obligations = money(baseline.formal_emis + baseline.informal_installments)
        return CurrentState(
            monthly_inflow=(baseline.conservative_monthly_inflow if reliable_cashflow else None),
            monthly_expenses=monthly_expenses,
            existing_monthly_obligations=obligations,
            monthly_surplus=(baseline.monthly_surplus if reliable_cashflow else None),
            safe_emi_min=(baseline.safe_emi_min if reliable_cashflow else None),
            safe_emi_max=(baseline.safe_emi_max if reliable_cashflow else None),
            available_balance_buffer=baseline.available_balance_buffer,
            overall_confidence=baseline.overall_confidence,
        )

    @staticmethod
    def _safety(baseline: FinancialBaseline, *, saving_uses_all_surplus: bool = False) -> SafetySummary:
        failed = [test.name for test in baseline.stress_tests if not test.passed]
        warning_keys: list[str] = []
        if baseline.new_credit_blocked:
            warning_keys.append("whatIf.safety.repaymentBlocked")
        if baseline.insufficient_history or baseline.cashflow_status == "INSUFFICIENT_DATA":
            warning_keys.append("whatIf.safety.insufficientHistory")
        if any(test.severity == "HIGH" and not test.passed for test in baseline.stress_tests):
            warning_keys.append("whatIf.safety.highStressFailure")
        if baseline.overall_confidence < Decimal("0.60"):
            warning_keys.append("whatIf.safety.lowConfidence")
        if saving_uses_all_surplus:
            warning_keys.append("whatIf.safety.noRemainingMargin")
        return SafetySummary(
            new_credit_blocked=baseline.new_credit_blocked,
            insufficient_history=baseline.insufficient_history,
            repayment_status=baseline.repayment_status,
            failed_stress_tests=failed,
            warning_keys=warning_keys,
            missing_fields=(
                ["monthly_inflow", "monthly_surplus", "safe_emi_min", "safe_emi_max"]
                if baseline.insufficient_history
                or baseline.cashflow_status == "INSUFFICIENT_DATA"
                else []
            ),
        )

    @classmethod
    def _loan_plan(
        cls, baseline: FinancialBaseline, goal: LoanReadinessGoal
    ) -> WhatIfResult:
        required_emi = compute_emi(
            goal.target_amount, goal.annual_interest_rate, goal.tenure_months
        )
        desired_buffer = money(goal.desired_buffer) if goal.desired_buffer is not None else None
        buffer_gap = (
            money(max(ZERO, desired_buffer - baseline.available_balance_buffer))
            if desired_buffer is not None
            else ZERO
        )
        monthly_buffer = (
            money(buffer_gap / Decimal(goal.deadline_months)) if buffer_gap else ZERO
        )

        snapshot = GoalSnapshot(
            type=goal.type,
            title=goal.title.strip(),
            target_amount=money(goal.target_amount),
            deadline_months=goal.deadline_months,
            annual_interest_rate=goal.annual_interest_rate,
            tenure_months=goal.tenure_months,
            desired_buffer=desired_buffer,
        )
        assumptions = [
            PlanAssumption(
                key="whatIf.assumption.safeEmiPolicy",
                params={"factor": float(baseline.safe_emi_max_factor)},
            ),
            PlanAssumption(
                key="whatIf.assumption.interestRate",
                params={"rate": float(goal.annual_interest_rate)},
            ),
            PlanAssumption(key="whatIf.assumption.noApprovalGuarantee"),
        ]

        if baseline.insufficient_history or baseline.cashflow_status == "INSUFFICIENT_DATA":
            blocked = baseline.new_credit_blocked
            return WhatIfResult(
                outcome="BLOCKED" if blocked else "INSUFFICIENT_DATA",
                goal=snapshot,
                current_state=cls._current_state(baseline, reliable_cashflow=False),
                required_state=RequiredState(
                    required_emi=required_emi,
                    required_monthly_surplus=None,
                    desired_buffer=desired_buffer,
                ),
                gap=FinancialGap(
                    emi_gap=None,
                    monthly_cashflow_gap=None,
                    monthly_savings_gap=None,
                    buffer_gap=None,
                    monthly_buffer_contribution=None,
                ),
                paths=(
                    [
                        PlanPath(
                            type="RESOLVE_REPAYMENT_BLOCK",
                            message_key="whatIf.path.resolveRepaymentBlock",
                        )
                    ]
                    if blocked
                    else []
                ),
                safety=cls._safety(baseline),
                assumptions=assumptions,
                message_keys=[
                    "whatIf.outcome.blocked" if blocked else "whatIf.outcome.insufficientData"
                ],
            )

        required_surplus = money(required_emi / baseline.safe_emi_max_factor)
        emi_gap = money(max(ZERO, required_emi - baseline.safe_emi_max))
        cashflow_gap = money(max(ZERO, required_surplus - baseline.monthly_surplus))
        required = RequiredState(
            required_emi=required_emi,
            required_monthly_surplus=required_surplus,
            desired_buffer=desired_buffer,
        )
        gap = FinancialGap(
            emi_gap=emi_gap,
            monthly_cashflow_gap=cashflow_gap,
            buffer_gap=buffer_gap,
            monthly_buffer_contribution=monthly_buffer,
        )

        if baseline.new_credit_blocked:
            return WhatIfResult(
                outcome="BLOCKED",
                goal=snapshot,
                current_state=cls._current_state(baseline),
                required_state=required,
                gap=gap,
                paths=[
                    PlanPath(
                        type="RESOLVE_REPAYMENT_BLOCK",
                        message_key="whatIf.path.resolveRepaymentBlock",
                    )
                ],
                safety=cls._safety(baseline),
                assumptions=assumptions,
                message_keys=["whatIf.outcome.blocked"],
            )

        outcome = (
            "ACHIEVABLE_NOW"
            if required_emi <= baseline.safe_emi_max and buffer_gap == 0
            else "ACHIEVABLE_WITH_CHANGES"
        )
        paths = cls._loan_paths(baseline, goal, cashflow_gap, buffer_gap, monthly_buffer)
        return WhatIfResult(
            outcome=outcome,
            goal=snapshot,
            current_state=cls._current_state(baseline),
            required_state=required,
            gap=gap,
            paths=paths,
            safety=cls._safety(baseline),
            assumptions=assumptions,
            message_keys=[
                "whatIf.outcome.achievableNow"
                if outcome == "ACHIEVABLE_NOW"
                else "whatIf.outcome.achievableWithChanges"
            ],
        )

    @classmethod
    def _loan_paths(
        cls,
        baseline: FinancialBaseline,
        goal: LoanReadinessGoal,
        cashflow_gap: Decimal,
        buffer_gap: Decimal,
        monthly_buffer: Decimal,
    ) -> list[PlanPath]:
        paths: list[PlanPath] = []
        if cashflow_gap > 0:
            total_expenses = baseline.household_expense + baseline.business_expense
            expense_available = cashflow_gap <= total_expenses
            paths.append(
                PlanPath(
                    type="REDUCE_EXPENSES",
                    message_key="whatIf.path.reduceExpenses",
                    available=expense_available,
                    monthly_amount=cashflow_gap,
                    expense_reduction=cashflow_gap if expense_available else None,
                )
            )
            paths.append(
                PlanPath(
                    type="INCREASE_INCOME",
                    message_key="whatIf.path.increaseIncome",
                    monthly_amount=cashflow_gap,
                    income_increase=cashflow_gap,
                )
            )
            expense_share = money(min(cashflow_gap / Decimal(2), total_expenses))
            income_share = money(cashflow_gap - expense_share)
            paths.append(
                PlanPath(
                    type="MIXED_CHANGE",
                    message_key="whatIf.path.mixedChange",
                    monthly_amount=cashflow_gap,
                    expense_reduction=expense_share,
                    income_increase=income_share,
                )
            )

            affordable_principal = compute_max_principal(
                baseline.safe_emi_max,
                goal.annual_interest_rate,
                goal.tenure_months,
            )
            paths.append(
                PlanPath(
                    type="LOWER_PRINCIPAL",
                    message_key="whatIf.path.lowerPrincipal",
                    available=affordable_principal > 0,
                    new_principal=affordable_principal,
                )
            )
            extended = first_affordable_tenure(
                goal.target_amount,
                goal.annual_interest_rate,
                baseline.safe_emi_max,
                goal.tenure_months,
            )
            paths.append(
                PlanPath(
                    type="EXTEND_LOAN_TENURE",
                    message_key="whatIf.path.extendLoanTenure",
                    available=extended is not None,
                    new_tenure_months=extended,
                )
            )

        if buffer_gap > 0:
            paths.append(
                PlanPath(
                    type="BUILD_BUFFER",
                    message_key="whatIf.path.buildBuffer",
                    monthly_amount=monthly_buffer,
                )
            )
        return paths

    @classmethod
    def _savings_plan(
        cls, baseline: FinancialBaseline, goal: SavingsTargetGoal
    ) -> WhatIfResult:
        remaining = money(max(ZERO, goal.target_amount - goal.current_goal_savings))
        required_monthly = money(remaining / Decimal(goal.deadline_months)) if remaining else ZERO
        contribution_factor = goal.conservative_contribution_factor or Decimal("1")

        snapshot = GoalSnapshot(
            type=goal.type,
            title=goal.title.strip(),
            target_amount=money(goal.target_amount),
            deadline_months=goal.deadline_months,
            current_goal_savings=money(goal.current_goal_savings),
        )
        assumptions = [
            PlanAssumption(
                key="whatIf.assumption.userDeclaredSavings",
                params={"amount": float(money(goal.current_goal_savings))},
            ),
            PlanAssumption(
                key="whatIf.assumption.savingsContributionFactor",
                params={"factor": float(contribution_factor)},
            ),
            PlanAssumption(key="whatIf.assumption.noApprovalGuarantee"),
        ]

        if baseline.insufficient_history or baseline.cashflow_status == "INSUFFICIENT_DATA":
            return WhatIfResult(
                outcome="INSUFFICIENT_DATA",
                goal=snapshot,
                current_state=cls._current_state(baseline, reliable_cashflow=False),
                required_state=RequiredState(
                    required_monthly_saving=required_monthly,
                    projected_goal_amount=None,
                ),
                gap=FinancialGap(
                    emi_gap=None,
                    monthly_cashflow_gap=None,
                    monthly_savings_gap=None,
                    buffer_gap=None,
                    monthly_buffer_contribution=None,
                ),
                paths=[],
                safety=cls._safety(baseline),
                assumptions=assumptions,
                message_keys=["whatIf.outcome.insufficientData"],
            )

        available_surplus = money(max(ZERO, baseline.monthly_surplus))
        modeled_contribution = money(available_surplus * contribution_factor)
        monthly_gap = money(max(ZERO, required_monthly - modeled_contribution))
        projected = money(goal.current_goal_savings + modeled_contribution * goal.deadline_months)
        uses_all_surplus = bool(
            contribution_factor == 1 and required_monthly > 0 and required_monthly >= available_surplus
        )
        required = RequiredState(
            required_monthly_saving=required_monthly,
            projected_goal_amount=projected,
        )
        gap = FinancialGap(monthly_savings_gap=monthly_gap)

        outcome = "ACHIEVABLE_NOW" if monthly_gap == 0 else "ACHIEVABLE_WITH_CHANGES"
        paths = cls._savings_paths(goal, monthly_gap, modeled_contribution, projected, baseline)
        return WhatIfResult(
            outcome=outcome,
            goal=snapshot,
            current_state=cls._current_state(baseline),
            required_state=required,
            gap=gap,
            paths=paths,
            safety=cls._safety(baseline, saving_uses_all_surplus=uses_all_surplus),
            assumptions=assumptions,
            message_keys=[
                "whatIf.outcome.achievableNow"
                if outcome == "ACHIEVABLE_NOW"
                else "whatIf.outcome.achievableWithChanges"
            ],
        )

    @staticmethod
    def _savings_paths(
        goal: SavingsTargetGoal,
        monthly_gap: Decimal,
        modeled_contribution: Decimal,
        projected: Decimal,
        baseline: FinancialBaseline,
    ) -> list[PlanPath]:
        if monthly_gap <= 0:
            return []
        total_expenses = baseline.household_expense + baseline.business_expense
        expense_available = monthly_gap <= total_expenses
        expense_share = money(min(monthly_gap / Decimal(2), total_expenses))
        income_share = money(monthly_gap - expense_share)
        paths = [
            PlanPath(
                type="REDUCE_EXPENSES",
                message_key="whatIf.path.reduceExpenses",
                available=expense_available,
                monthly_amount=monthly_gap,
                expense_reduction=monthly_gap if expense_available else None,
            ),
            PlanPath(
                type="INCREASE_INCOME",
                message_key="whatIf.path.increaseIncome",
                monthly_amount=monthly_gap,
                income_increase=monthly_gap,
            ),
            PlanPath(
                type="MIXED_CHANGE",
                message_key="whatIf.path.mixedChange",
                monthly_amount=monthly_gap,
                expense_reduction=expense_share,
                income_increase=income_share,
            ),
        ]
        if modeled_contribution > 0:
            remaining = max(ZERO, goal.target_amount - goal.current_goal_savings)
            months = int((remaining / modeled_contribution).to_integral_value(rounding=ROUND_CEILING))
            paths.append(
                PlanPath(
                    type="EXTEND_SAVINGS_DEADLINE",
                    message_key="whatIf.path.extendSavingsDeadline",
                    new_deadline_months=months,
                )
            )
        paths.append(
            PlanPath(
                type="REDUCE_TARGET",
                message_key="whatIf.path.reduceTarget",
                new_target_amount=projected,
            )
        )
        return paths
