"""
common/reason_codes.py

Canonical reason-code registry for all FinMitra components.

Prefix convention:
  EV  — Evidence Engine      (Person 1)
  CF  — Cash-Flow Model      (Person 2)
  RP  — Repayment Engine     (Person 3)
  CP  — Capacity Engine      (Person 4)

Person 4 owns CPxx codes and must not reuse codes from other prefixes.
"""
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class _ReasonCode:
    code: str
    description: str

    def __str__(self) -> str:
        return self.code


class ReasonCodes:
    """Static registry of all reason codes."""

    # ------------------------------------------------------------------
    # Capacity Engine (Person 4)
    # ------------------------------------------------------------------
    CP01 = _ReasonCode("CP01", "Positive monthly surplus — borrower has repayment headroom")
    CP02 = _ReasonCode("CP02", "Limited monthly surplus — repayment capacity constrained")
    CP03 = _ReasonCode("CP03", "High existing obligations relative to income")
    CP04 = _ReasonCode("CP04", "New credit blocked by repayment engine")
    CP05 = _ReasonCode("CP05", "Stress test failure — affordability under pressure")
    CP06 = _ReasonCode("CP06", "Insufficient affordability data")
    CP07 = _ReasonCode("CP07", "Outstanding delinquent amount present")
    CP08 = _ReasonCode("CP08", "Requested loan EMI within safe capacity")
    CP09 = _ReasonCode("CP09", "Requested loan EMI exceeds safe capacity")
    CP10 = _ReasonCode("CP10", "Zero or negative surplus — no affordability capacity")
    CP11 = _ReasonCode("CP11", "Strong surplus — substantial repayment headroom")
    CP12 = _ReasonCode("CP12", "Income volatility is elevated — stress tests relevant")
    CP13 = _ReasonCode("CP13", "Seasonal income profile — lowest-inflow period used for stress test")

    # ------------------------------------------------------------------
    # Evidence Engine stubs (Person 1) — read-only in Person 4 context
    # ------------------------------------------------------------------
    EV01 = _ReasonCode("EV01", "Evidence quality: high — data is consistent and complete")
    EV02 = _ReasonCode("EV02", "Evidence quality: medium")
    EV03 = _ReasonCode("EV03", "Evidence quality: low — data has gaps or anomalies")
    EV04 = _ReasonCode("EV04", "Insufficient transaction history")

    # ------------------------------------------------------------------
    # Cash-Flow Model stubs (Person 2) — read-only in Person 4 context
    # ------------------------------------------------------------------
    CF01 = _ReasonCode("CF01", "Strong cash-flow stability")
    CF02 = _ReasonCode("CF02", "Moderate cash-flow stability")
    CF03 = _ReasonCode("CF03", "Weak cash-flow stability")

    # ------------------------------------------------------------------
    # Repayment Engine stubs (Person 3) — read-only in Person 4 context
    # ------------------------------------------------------------------
    RP01 = _ReasonCode("RP01", "Consistent historical repayment behaviour")
    RP02 = _ReasonCode("RP02", "Partial repayment history")
    RP03 = _ReasonCode("RP03", "Delinquency detected — new credit blocked")
