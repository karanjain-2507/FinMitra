"""Deterministic repayment engine. Cash-flow and evidence engines do not override status."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from common.config import COMPONENT_REPAYMENT, COMPONENT_VERSION
from common.reason_codes import (
    RP00_BASELINE,
    RP01_MATERIALLY_UNPAID,
    RP02_DELINQUENT,
    RP03_BEHIND_SCHEDULE,
    RP04_COMPLETED_CYCLES,
    RP05_ON_TIME,
    RP06_OUTSTANDING_PRINCIPAL,
    RP07_DIGITALLY_MATCHED,
    RP08_CONTRADICTION,
    RP09_SUPPLIER_CONFIRMED,
    RP10_FULLY_REPAID,
    RP11_INSUFFICIENT_EVIDENCE,
    RP12_HARD_CAP,
    RP13_CURRENT_ON_SCHEDULE,
    RP14_OLD_ACTIVE_MISSING,
    RP15_DECLARED_COMPLETED_UNDERPAID,
)
from common.schemas import BorrowerInput, ComponentResult, Reason
from common.validation import validate_borrower_input
from repayment.features import (
    COMPLETED_LOAN_REPAYMENT_RATIO,
    compute_features,
    declared_completed,
    declared_overdue,
)
from repayment.matching import SELF_DECLARED, is_digitally_matched, is_verified_match
from repayment.schedule import build_full_schedule

STATUS_SEVERELY_UNPAID = "SEVERELY_UNPAID"
STATUS_DELINQUENT = "DELINQUENT"
STATUS_BEHIND_SCHEDULE = "BEHIND_SCHEDULE"
STATUS_CURRENT = "CURRENT"
STATUS_COMPLETED = "COMPLETED"
STATUS_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

STATUS_RANK = {
    STATUS_SEVERELY_UNPAID: 0,
    STATUS_DELINQUENT: 1,
    STATUS_BEHIND_SCHEDULE: 2,
    STATUS_INSUFFICIENT_EVIDENCE: 3,
    STATUS_CURRENT: 4,
    STATUS_COMPLETED: 5,
}

OLD_LOAN_DAYS = 60
BEHIND_SCHEDULE_DPD = 30
MATERIAL_OUTSTANDING_RATIO = 0.20
COMPLETION_THRESHOLD = COMPLETED_LOAN_REPAYMENT_RATIO
HARD_CAP_VALUE = 35.0


def assess(profile: BorrowerInput) -> ComponentResult:
    warnings = validate_borrower_input(profile)
    evaluation_date = profile.evaluation_date or date.today()
    features, loan_metrics, match_warnings = compute_features(profile, evaluation_date)
    warnings.extend(match_warnings)

    for metrics in loan_metrics:
        metrics["status"] = _classify_loan(metrics, evaluation_date)

    _fill_status_counts(features, loan_metrics)
    status = _portfolio_status(loan_metrics, features)
    if features.get("no_prior_loans"):
        warnings.append(
            "No prior loans declared; this is an empty obligation history, not thin repayment evidence"
        )
    if features.get("completed_credit_cycles"):
        warnings.append(
            "completed_credit_cycles counts completed declared loans only; "
            "the schema supports one repayment cycle per loan"
        )

    score, reasons = _score(status, features, loan_metrics)
    blocked, hard_cap, score, reasons = _credit_block(status, features, score, reasons)
    confidence = _confidence(profile, features, status, loan_metrics)

    return ComponentResult(
        component=COMPONENT_REPAYMENT,
        version=COMPONENT_VERSION,
        score=score,
        status=status,
        confidence=confidence,
        features=features,
        reasons=reasons,
        warnings=warnings,
        new_credit_blocked=blocked,
        hard_cap=hard_cap,
    )


def _classify_loan(metrics: dict[str, Any], evaluation_date: date) -> str:
    loan = metrics["loan"]
    repaid = float(metrics["digitally_matched_amount"])
    expected_count = metrics["payments_expected"]
    paid_count = metrics["payments_made"]
    unpaid = metrics["unpaid_expected"]
    dpd = max(0, metrics["maximum_days_past_due"] or 0)
    completion = metrics["completion_ratio"]
    has_schedule = bool(metrics["has_schedule"])
    expected_count_n = expected_count or 0
    paid_count_n = paid_count or 0
    unpaid_n = unpaid or 0.0
    missing = max(0, expected_count_n - paid_count_n)
    full_schedule = build_full_schedule(loan) if has_schedule else []

    if not has_schedule and repaid <= 0.01:
        return STATUS_INSUFFICIENT_EVIDENCE

    due_unpaid = has_schedule and expected_count_n > 0 and unpaid_n > 0.01
    overdue_without_pay = (declared_overdue(loan) or due_unpaid) and repaid <= 0.01

    if overdue_without_pay and (declared_overdue(loan) or expected_count_n > 0):
        return STATUS_SEVERELY_UNPAID

    if declared_completed(loan) and (completion is None or completion < COMPLETION_THRESHOLD):
        return STATUS_DELINQUENT

    full_schedule_paid = bool(full_schedule) and repaid >= COMPLETION_THRESHOLD * sum(
        item.amount for item in full_schedule
    )
    if completion is not None and completion >= COMPLETION_THRESHOLD:
        if declared_completed(loan) or metrics["all_installments_covered"] or full_schedule_paid:
            return STATUS_COMPLETED
    if full_schedule_paid:
        return STATUS_COMPLETED

    if declared_overdue(loan):
        return STATUS_DELINQUENT

    if has_schedule and expected_count_n > 0 and paid_count_n >= expected_count_n and unpaid_n <= 0.01:
        return STATUS_CURRENT

    if has_schedule and missing > 0 and paid_count_n > 0 and dpd <= BEHIND_SCHEDULE_DPD:
        return STATUS_BEHIND_SCHEDULE

    if has_schedule and missing > 0 and dpd > BEHIND_SCHEDULE_DPD:
        return STATUS_DELINQUENT

    if has_schedule and missing > 0 and paid_count_n == 0:
        return STATUS_SEVERELY_UNPAID

    if repaid <= 0.01:
        return STATUS_INSUFFICIENT_EVIDENCE

    return STATUS_CURRENT


def _portfolio_status(loan_metrics: list[dict[str, Any]], features: dict[str, Any]) -> str:
    if not loan_metrics:
        return STATUS_CURRENT
    return min(
        (item["status"] for item in loan_metrics),
        key=lambda status: STATUS_RANK[status],
    )


def _fill_status_counts(features: dict[str, Any], loan_metrics: list[dict[str, Any]]) -> None:
    completed = sum(1 for item in loan_metrics if item["status"] == STATUS_COMPLETED)
    delinquent = sum(
        1
        for item in loan_metrics
        if item["status"] in {STATUS_DELINQUENT, STATUS_SEVERELY_UNPAID}
    )
    current = sum(1 for item in loan_metrics if item["status"] == STATUS_CURRENT)
    features["completed_credit_cycles"] = completed
    features["completed_loan_count"] = completed if loan_metrics else 0
    features["delinquent_loan_count"] = delinquent if loan_metrics else 0
    features["current_loan_count"] = current if loan_metrics else 0


def _score(
    status: str, features: dict[str, Any], loan_metrics: list[dict[str, Any]]
) -> tuple[Optional[float], list[Reason]]:
    reasons: list[Reason] = []
    score = 0.0

    def apply(code: str, direction: str, impact: float, message: str) -> None:
        nonlocal score
        score += impact
        reasons.append(
            Reason(code=code, direction=direction, impact=round(impact, 2), message=message)
        )

    apply(RP00_BASELINE, "NEUTRAL", 50.0, "Neutral repayment baseline")

    if features.get("no_prior_loans"):
        apply(
            RP11_INSUFFICIENT_EVIDENCE,
            "NEUTRAL",
            0.0,
            "No prior loans declared; empty history is not scored as thin-file evidence",
        )

    cycles = int(features.get("completed_credit_cycles") or 0)
    if cycles > 0:
        apply(
            RP04_COMPLETED_CYCLES,
            "POSITIVE",
            min(8.0, 4.0 * cycles),
            f"{cycles} completed declared loan cycle(s); one cycle per loan record",
        )

    if status == STATUS_SEVERELY_UNPAID:
        apply(
            RP01_MATERIALLY_UNPAID,
            "NEGATIVE",
            -40.0,
            "One declared informal loan is materially unpaid",
        )
    elif status == STATUS_DELINQUENT:
        apply(RP02_DELINQUENT, "NEGATIVE", -25.0, "At least one loan is delinquent")
        if any(
            declared_completed(item["loan"])
            and (item["completion_ratio"] is None or item["completion_ratio"] < COMPLETION_THRESHOLD)
            for item in loan_metrics
        ):
            apply(
                RP15_DECLARED_COMPLETED_UNDERPAID,
                "NEGATIVE",
                -10.0,
                "A loan is declared completed but repayment completion is below 90%",
            )
        if any(
            item["status"] == STATUS_DELINQUENT
            and not declared_overdue(item["loan"])
            and (item["payments_expected"] or 0) > (item["payments_made"] or 0)
            for item in loan_metrics
        ):
            apply(
                RP14_OLD_ACTIVE_MISSING,
                "NEGATIVE",
                -8.0,
                "An old active loan has expected installments with missing payments",
            )
    elif status == STATUS_BEHIND_SCHEDULE:
        apply(
            RP03_BEHIND_SCHEDULE,
            "NEGATIVE",
            -10.0,
            "Expected installments are not fully paid on the reconstructed schedule",
        )
    elif status == STATUS_CURRENT and not features.get("no_prior_loans"):
        apply(
            RP13_CURRENT_ON_SCHEDULE,
            "POSITIVE",
            10.0,
            "Expected installments due as of the evaluation date are paid",
        )
    elif status == STATUS_COMPLETED:
        apply(RP10_FULLY_REPAID, "POSITIVE", 12.0, "Loan obligations are fully repaid")
    elif status == STATUS_INSUFFICIENT_EVIDENCE:
        apply(
            RP11_INSUFFICIENT_EVIDENCE,
            "NEGATIVE",
            -5.0,
            "Repayment history is too thin to support a strong repayment assessment",
        )

    on_time = features.get("on_time_payment_ratio")
    if on_time is not None and status not in {STATUS_SEVERELY_UNPAID, STATUS_INSUFFICIENT_EVIDENCE}:
        impact = round(10.0 * on_time, 2)
        apply(
            RP05_ON_TIME,
            "POSITIVE" if impact >= 0 else "NEGATIVE",
            impact,
            f"On-time payment ratio is {on_time:.2f}",
        )

    outstanding_ratio = features.get("outstanding_principal_ratio")
    if (
        outstanding_ratio is not None
        and outstanding_ratio > 0
        and status not in {STATUS_SEVERELY_UNPAID, STATUS_INSUFFICIENT_EVIDENCE}
    ):
        impact = round(-12.0 * outstanding_ratio, 2)
        apply(
            RP06_OUTSTANDING_PRINCIPAL,
            "NEGATIVE",
            impact,
            f"Outstanding principal ratio is {outstanding_ratio:.2f}",
        )

    digital = features.get("digitally_matched_repayment_ratio")
    if digital is not None:
        impact = round(8.0 * digital, 2)
        apply(
            RP07_DIGITALLY_MATCHED,
            "POSITIVE",
            impact,
            f"Digitally matched repayment ratio is {digital:.2f}",
        )

    supplier = features.get("supplier_confirmed_repayment_ratio")
    if supplier is not None and supplier > 0:
        impact = round(6.0 * supplier, 2)
        apply(
            RP09_SUPPLIER_CONFIRMED,
            "POSITIVE",
            impact,
            f"Supplier-confirmed repayment ratio is {supplier:.2f}",
        )

    contradictions = features.get("contradictory_declarations") or 0
    if contradictions:
        impact = -8.0 * min(int(contradictions), 3)
        apply(
            RP08_CONTRADICTION,
            "NEGATIVE",
            impact,
            "Repayment claims contradict transaction or declared-loan evidence",
        )

    score = round(min(100.0, max(0.0, score)), 0)
    return score, reasons


def _credit_block(
    status: str,
    features: dict[str, Any],
    score: Optional[float],
    reasons: list[Reason],
) -> tuple[bool, Optional[float], Optional[float], list[Reason]]:
    outstanding_ratio = features.get("outstanding_principal_ratio") or 0.0
    dpd = max(0, features.get("maximum_days_past_due") or 0)
    material = status == STATUS_SEVERELY_UNPAID or (
        status == STATUS_DELINQUENT
        and (outstanding_ratio >= MATERIAL_OUTSTANDING_RATIO or dpd >= BEHIND_SCHEDULE_DPD)
    )
    if not material:
        return False, None, score, reasons

    blocked = True
    hard_cap = HARD_CAP_VALUE
    if score is not None and score > hard_cap:
        impact = round(hard_cap - score, 2)
        score = hard_cap
        reasons.append(
            Reason(
                code=RP12_HARD_CAP,
                direction="NEGATIVE",
                impact=impact,
                message="Hard cap applied because of a materially unpaid overdue obligation",
            )
        )
    return blocked, hard_cap, score, reasons


def _confidence(
    profile: BorrowerInput,
    features: dict[str, Any],
    status: str,
    loan_metrics: list[dict[str, Any]],
) -> float:
    """Evidence quality only. Never used to override known delinquency."""

    verified_amt = 0.0
    matched_unverified_amt = 0.0
    self_declared_amt = 0.0
    for metrics in loan_metrics:
        for match in metrics.get("matches") or []:
            amount = float(match.matched_amount)
            if match.match_method == SELF_DECLARED or not is_digitally_matched(match):
                self_declared_amt += amount
            elif is_verified_match(match):
                verified_amt += amount
            else:
                matched_unverified_amt += amount

    total = verified_amt + matched_unverified_amt + self_declared_amt
    value = 0.40
    if total > 0:
        value += 0.50 * (verified_amt / total)
        value += 0.22 * (matched_unverified_amt / total)
        value -= 0.10 * (self_declared_amt / total)
    elif features.get("no_prior_loans"):
        value = 0.55
    else:
        value -= 0.15

    contradictions = features.get("contradictory_declarations") or 0
    if contradictions:
        value -= min(0.24, 0.08 * float(contradictions))

    if status == STATUS_INSUFFICIENT_EVIDENCE:
        value -= 0.18

    if profile.evidence is not None and profile.evidence.evidence_confidence is not None:
        value = 0.80 * value + 0.20 * float(profile.evidence.evidence_confidence)

    return round(min(1.0, max(0.05, value)), 4)
