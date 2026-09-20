"""Adapters from the integrated assessment result to the What If baseline."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .calculations import money
from .schemas import FinancialBaseline, StressTestSummary


class BaselineDataError(ValueError):
    """Raised when an assessment lacks authoritative planning fields."""


def _required(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping or mapping[key] is None:
        raise BaselineDataError(f"missing {context}.{key}")
    return mapping[key]


def baseline_from_assessment(result: dict[str, Any]) -> FinancialBaseline:
    try:
        profile = _required(result, "profile", "assessment")
        capacity = _required(profile, "capacity", "profile")
        features = _required(capacity, "features", "profile.capacity")
        safe_emi = _required(capacity, "safe_emi", "profile.capacity")
        repayment = _required(profile, "repayment", "profile")
        evidence = _required(profile, "evidence", "profile")
        cashflow = _required(profile, "cashflow", "profile")

        stress_tests = [
            StressTestSummary(
                name=str(_required(item, "name", "stress_test")),
                passed=bool(_required(item, "passed", "stress_test")),
                severity=str(item.get("severity", "UNKNOWN")),
                stressed_monthly_surplus=(
                    money(item["stressed_monthly_surplus"])
                    if item.get("stressed_monthly_surplus") is not None
                    else None
                ),
            )
            for item in capacity.get("stress_tests", [])
        ]

        return FinancialBaseline(
            borrower_id=result.get("borrower_id"),
            evaluation_date=_required(result, "evaluation_date", "assessment"),
            conservative_monthly_inflow=money(
                _required(features, "conservative_monthly_inflow", "capacity.features")
            ),
            household_expense=money(
                _required(features, "essential_household_expense", "capacity.features")
            ),
            business_expense=money(
                _required(features, "essential_business_expense", "capacity.features")
            ),
            formal_emis=money(
                _required(features, "existing_formal_emis", "capacity.features")
            ),
            informal_installments=money(
                _required(features, "existing_informal_installments", "capacity.features")
            ),
            monthly_surplus=money(
                _required(features, "monthly_surplus", "capacity.features")
            ),
            available_balance_buffer=money(
                _required(features, "available_balance_buffer", "capacity.features")
            ),
            safe_emi_min=money(_required(safe_emi, "minimum", "capacity.safe_emi")),
            safe_emi_max=money(_required(safe_emi, "maximum", "capacity.safe_emi")),
            safe_emi_max_factor=Decimal(
                str(_required(features, "safe_emi_max_factor", "capacity.features"))
            ),
            new_credit_blocked=bool(
                _required(repayment, "new_credit_blocked", "profile.repayment")
            ),
            repayment_status=str(repayment.get("status", "UNKNOWN")),
            insufficient_history=bool(evidence.get("insufficient_history", False)),
            cashflow_status=str(cashflow.get("status", "UNKNOWN")),
            overall_confidence=Decimal(
                str(_required(profile, "overall_confidence", "profile"))
            ),
            stress_tests=stress_tests,
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, BaselineDataError):
            raise
        raise BaselineDataError(str(exc)) from exc
