"""Pure Decimal calculations used by the What If engine."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANTUM = Decimal("0.01")


def money(value: Decimal | int | float | str) -> Decimal:
    """Convert to a finite two-decimal currency value."""
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("monetary values must be finite")
    return result.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def compute_emi(
    principal: Decimal,
    annual_interest_rate: Decimal,
    tenure_months: int,
) -> Decimal:
    if principal <= 0:
        raise ValueError("principal must be greater than zero")
    if annual_interest_rate < 0:
        raise ValueError("annual_interest_rate must be non-negative")
    if tenure_months <= 0:
        raise ValueError("tenure_months must be greater than zero")
    if annual_interest_rate == 0:
        return money(principal / Decimal(tenure_months))

    monthly_rate = annual_interest_rate / Decimal(12)
    factor = (Decimal(1) + monthly_rate) ** tenure_months
    return money(principal * monthly_rate * factor / (factor - Decimal(1)))


def compute_max_principal(
    emi: Decimal,
    annual_interest_rate: Decimal,
    tenure_months: int,
) -> Decimal:
    if emi <= 0:
        return Decimal("0.00")
    if annual_interest_rate < 0:
        raise ValueError("annual_interest_rate must be non-negative")
    if tenure_months <= 0:
        raise ValueError("tenure_months must be greater than zero")
    if annual_interest_rate == 0:
        return money(emi * Decimal(tenure_months))

    monthly_rate = annual_interest_rate / Decimal(12)
    factor = (Decimal(1) + monthly_rate) ** tenure_months
    return money(emi * (factor - Decimal(1)) / (monthly_rate * factor))


def first_affordable_tenure(
    principal: Decimal,
    annual_interest_rate: Decimal,
    safe_emi_max: Decimal,
    start_months: int,
    maximum_months: int = 360,
) -> int | None:
    if safe_emi_max <= 0:
        return None
    for tenure in range(start_months + 1, maximum_months + 1):
        if compute_emi(principal, annual_interest_rate, tenure) <= safe_emi_max:
            return tenure
    return None
