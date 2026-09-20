"""Deterministic repayment features. Missing values are None, never implicit zeros.

Installment coverage and loan-completion are different thresholds:

* INSTALLMENT_COVERAGE_RATIO (0.95): an installment slot counts as paid
* COMPLETED_LOAN_REPAYMENT_RATIO (0.90): a loan declared complete is valid only
  if at least 90% of principal is actually repaid

completed_credit_cycles counts declared loans classified COMPLETED. Each Loan
record is one obligation with one reconstructed schedule; the schema cannot
represent multiple historical cycles per loan.

Supplier confirmation is not inferred from relationship_type=SUPPLIER or from
Transaction.verified. It is counted only when an explicit supplier-confirmation
flag exists on the loan, claim, or transaction (extensible extra field).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from common.schemas import BorrowerInput, Loan, Repayment, Transaction
from repayment.matching import (
    SELF_DECLARED,
    is_digitally_matched,
    is_verified_match,
    match_repayments,
)
from repayment.models import InstallmentAllocation, PaymentMatch
from repayment.schedule import (
    build_full_schedule,
    can_build_schedule,
    days_past_due,
    expected_installments_as_of,
)

SUPPLIER_RELATIONSHIPS = {"SUPPLIER", "TRADE", "VENDOR", "WHOLESALER"}
OVERDUE_STATUSES = {"OVERDUE", "DELINQUENT", "DEFAULTED", "SEVERELY_UNPAID", "UNPAID", "LATE"}
COMPLETED_STATUSES = {"COMPLETED", "PAID", "CLOSED", "SETTLED", "REPAID"}
INSTALLMENT_COVERAGE_RATIO = 0.95
COMPLETED_LOAN_REPAYMENT_RATIO = 0.90
COVERAGE_RATIO = INSTALLMENT_COVERAGE_RATIO
SUPPLIER_CONFIRMATION_FIELDS = (
    "supplier_confirmed",
    "supplier_confirmation",
    "confirmed_by_supplier",
)


def ratio(numerator: float, denominator: float) -> Optional[float]:
    if denominator <= 0:
        return None
    value = numerator / denominator
    return max(0.0, min(1.0, value))


def is_supplier_loan(loan: Loan) -> bool:
    """Lender relationship only. This is not supplier-confirmed repayment."""

    return (loan.relationship_type or "").upper() in SUPPLIER_RELATIONSHIPS


def declared_overdue(loan: Loan) -> bool:
    return (loan.declared_status or "").upper() in OVERDUE_STATUSES


def declared_completed(loan: Loan) -> bool:
    return (loan.declared_status or "").upper() in COMPLETED_STATUSES


def installment_is_covered(paid_amount: float, expected_amount: float) -> bool:
    if expected_amount <= 0:
        return False
    return paid_amount >= INSTALLMENT_COVERAGE_RATIO * expected_amount


def digitally_matched_matches(matches: list[PaymentMatch]) -> list[PaymentMatch]:
    return [match for match in matches if is_digitally_matched(match)]


def verified_matches(matches: list[PaymentMatch]) -> list[PaymentMatch]:
    """Matches whose underlying transaction has verified=True."""

    return [match for match in matches if is_verified_match(match)]


def self_declared_matches(matches: list[PaymentMatch]) -> list[PaymentMatch]:
    return [match for match in matches if match.match_method == SELF_DECLARED]


def _explicit_true(obj: Any, field: str) -> bool:
    if obj is None:
        return False
    if getattr(obj, field, None) is True:
        return True
    extra = getattr(obj, "model_extra", None) or {}
    return extra.get(field) is True


def has_supplier_confirmation(
    *,
    loan: Loan,
    match: PaymentMatch,
    transactions_by_id: dict[str, Transaction],
    claims_by_id: dict[str, Repayment],
) -> bool:
    claim = claims_by_id.get(match.repayment_id)
    tx = transactions_by_id.get(match.transaction_id) if match.transaction_id else None
    for obj in (loan, match, claim, tx):
        for field in SUPPLIER_CONFIRMATION_FIELDS:
            if _explicit_true(obj, field):
                return True
    return False


def allocate_installments(
    loan: Loan,
    matches: list[PaymentMatch],
    evaluation_date: date,
) -> list[InstallmentAllocation]:
    """Oldest-due-first allocation.

    Expected installments are filled in due-date order. Digitally matched
    payments (verified or not) are consumed in payment-date order. Self-declared
    amounts are not allocated.
    """

    expected = sorted(
        expected_installments_as_of(loan, evaluation_date),
        key=lambda item: (item.due_date, item.installment_index),
    )
    remaining: list[list[Any]] = []
    for match in digitally_matched_matches(matches):
        remaining.append(
            [match.payment_date or date.max, float(match.matched_amount), match]
        )
    remaining.sort(key=lambda item: (item[0], item[2].repayment_id))

    allocations: list[InstallmentAllocation] = []
    for installment in expected:
        need = float(installment.amount)
        paid = 0.0
        paid_date: Optional[date] = None
        digital = False
        for row in remaining:
            if need <= 0.01:
                break
            if row[1] <= 0:
                continue
            take = min(need, row[1])
            row[1] -= take
            paid += take
            need -= take
            digital = True
            pay_date = row[0] if row[0] != date.max else None
            if pay_date is not None and (paid_date is None or pay_date < paid_date):
                paid_date = pay_date

        covered = installment_is_covered(paid, installment.amount)
        on_time = covered and paid_date is not None and paid_date <= installment.due_date
        allocations.append(
            InstallmentAllocation(
                loan_id=loan.loan_id,
                installment_index=installment.installment_index,
                due_date=installment.due_date,
                expected_amount=float(installment.amount),
                paid_amount=paid,
                paid_date=paid_date,
                on_time=on_time,
                digitally_matched=digital and covered,
            )
        )
    return allocations


def compute_loan_metrics(
    loan: Loan,
    matches: list[PaymentMatch],
    evaluation_date: date,
    *,
    transactions_by_id: Optional[dict[str, Transaction]] = None,
    claims_by_id: Optional[dict[str, Repayment]] = None,
) -> dict[str, Any]:
    tx_index = transactions_by_id or {}
    claim_index = claims_by_id or {}
    allocations = allocate_installments(loan, matches, evaluation_date)
    digital_amount = sum(match.matched_amount for match in digitally_matched_matches(matches))
    verified_amount = sum(match.matched_amount for match in verified_matches(matches))
    declared_amount = sum(match.matched_amount for match in self_declared_matches(matches))
    expected_amount = sum(item.expected_amount for item in allocations)
    payments_expected = len(allocations)
    payments_made = sum(
        1 for item in allocations if installment_is_covered(item.paid_amount, item.expected_amount)
    )
    on_time_count = sum(1 for item in allocations if item.on_time)
    on_time_count = min(on_time_count, payments_made)
    unpaid_expected = max(0.0, expected_amount - sum(item.paid_amount for item in allocations))

    dpd_values = [
        days_past_due(
            item.due_date,
            evaluation_date,
            covered=installment_is_covered(item.paid_amount, item.expected_amount),
            paid_date=item.paid_date,
        )
        for item in allocations
    ]
    full_schedule = build_full_schedule(loan)
    future_dpd = [
        days_past_due(item.due_date, evaluation_date, covered=False)
        for item in full_schedule
        if item.due_date > evaluation_date
    ]
    all_dpd = dpd_values + future_dpd
    maximum_dpd = max((max(0, value) for value in all_dpd), default=None)
    if maximum_dpd is None and (allocations or full_schedule):
        maximum_dpd = 0

    supplier_confirmed_amount = sum(
        match.matched_amount
        for match in digitally_matched_matches(matches)
        if has_supplier_confirmation(
            loan=loan,
            match=match,
            transactions_by_id=tx_index,
            claims_by_id=claim_index,
        )
    )
    confirmation_present = any(
        has_supplier_confirmation(
            loan=loan,
            match=match,
            transactions_by_id=tx_index,
            claims_by_id=claim_index,
        )
        for match in matches
    ) or any(
        _explicit_true(loan, field) for field in SUPPLIER_CONFIRMATION_FIELDS
    )

    outstanding = max(0.0, float(loan.principal_amount) - digital_amount)
    covered_due = (
        bool(allocations)
        and all(installment_is_covered(item.paid_amount, item.expected_amount) for item in allocations)
        and len(full_schedule) > 0
        and len(allocations) == len(full_schedule)
    )
    completion = ratio(digital_amount, float(loan.principal_amount))

    status_contradiction = 1 if (
        declared_completed(loan)
        and (completion is None or completion < COMPLETED_LOAN_REPAYMENT_RATIO)
    ) else 0
    match_contradictions = sum(1 for match in matches if match.contradictory)

    return {
        "loan": loan,
        "matches": matches,
        "allocations": allocations,
        "verified_amount": verified_amount,
        "digitally_matched_amount": digital_amount,
        "declared_unverified_amount": declared_amount,
        "expected_amount": expected_amount if can_build_schedule(loan) else None,
        "payments_expected": payments_expected if can_build_schedule(loan) else None,
        "payments_made": payments_made if can_build_schedule(loan) else None,
        "on_time_count": on_time_count if can_build_schedule(loan) else None,
        "unpaid_expected": unpaid_expected if can_build_schedule(loan) else None,
        "maximum_days_past_due": maximum_dpd,
        "outstanding_principal": outstanding,
        "has_schedule": can_build_schedule(loan),
        "contradictory_declarations": match_contradictions + status_contradiction,
        "supplier_confirmed_amount": supplier_confirmed_amount,
        "supplier_confirmation_available": confirmation_present,
        "all_installments_covered": covered_due,
        "completion_ratio": completion,
    }


def compute_features(
    profile: BorrowerInput, evaluation_date: Optional[date] = None
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    eval_date = evaluation_date or profile.evaluation_date or date.today()
    match_warnings: list[str] = []
    all_matches = match_repayments(profile, eval_date, warnings=match_warnings)
    tx_index = {tx.transaction_id: tx for tx in profile.transactions}
    claim_index = {claim.repayment_id: claim for claim in profile.repayment_claims}
    loan_metrics: list[dict[str, Any]] = []

    for loan in profile.informal_loans:
        loan_matches = [match for match in all_matches if match.loan_id == loan.loan_id]
        loan_metrics.append(
            compute_loan_metrics(
                loan,
                loan_matches,
                eval_date,
                transactions_by_id=tx_index,
                claims_by_id=claim_index,
            )
        )

    total_loans = len(profile.informal_loans)
    borrowed = sum(float(loan.principal_amount) for loan in profile.informal_loans)
    due_values = [item["expected_amount"] for item in loan_metrics if item["expected_amount"] is not None]
    repaid = sum(item["digitally_matched_amount"] for item in loan_metrics)
    verified = sum(item["verified_amount"] for item in loan_metrics)
    payments_expected_values = [
        item["payments_expected"] for item in loan_metrics if item["payments_expected"] is not None
    ]
    payments_made_values = [
        item["payments_made"] for item in loan_metrics if item["payments_made"] is not None
    ]
    on_time_values = [item["on_time_count"] for item in loan_metrics if item["on_time_count"] is not None]
    dpd_values = [
        max(0, item["maximum_days_past_due"])
        for item in loan_metrics
        if item["maximum_days_past_due"] is not None
    ]
    outstanding = sum(item["outstanding_principal"] for item in loan_metrics)
    digital = repaid
    declared = sum(item["declared_unverified_amount"] for item in loan_metrics)
    evidence_total = digital + declared
    supplier = sum(item["supplier_confirmed_amount"] for item in loan_metrics)
    confirmation_available = any(item["supplier_confirmation_available"] for item in loan_metrics)
    contradictions = sum(item["contradictory_declarations"] for item in loan_metrics)

    payments_expected = sum(payments_expected_values) if payments_expected_values else None
    payments_made = sum(payments_made_values) if payments_made_values else None
    on_time_count = sum(on_time_values) if on_time_values else None
    if on_time_count is not None and payments_made is not None:
        on_time_count = min(on_time_count, payments_made)

    features: dict[str, Any] = {
        "total_loans_declared": total_loans,
        "no_prior_loans": total_loans == 0,
        "completed_credit_cycles": None,
        "completed_credit_cycles_note": (
            "Each declared loan is at most one completed cycle; richer multi-cycle "
            "history is not present in the schema"
        ),
        "total_amount_borrowed": borrowed if total_loans else None,
        "total_amount_due": sum(due_values) if due_values else None,
        "total_amount_repaid": repaid if total_loans else None,
        "self_declared_repayment_amount": declared if total_loans else None,
        "repayment_evidence_amount": evidence_total if total_loans else None,
        "repayment_completion_ratio": ratio(repaid, borrowed) if total_loans else None,
        "payments_expected": payments_expected,
        "payments_made": payments_made,
        "on_time_payment_ratio": ratio(float(on_time_count or 0), float(payments_expected or 0))
        if payments_expected is not None
        else None,
        "maximum_days_past_due": max(dpd_values) if dpd_values else (0 if total_loans == 0 else None),
        "outstanding_principal": outstanding if total_loans else None,
        "outstanding_principal_ratio": ratio(outstanding, borrowed) if total_loans else None,
        "digitally_matched_repayment_ratio": ratio(digital, evidence_total) if evidence_total > 0 else None,
        "verified_repayment_ratio": ratio(verified, repaid) if repaid > 0 else None,
        "supplier_confirmed_repayment_ratio": (
            ratio(supplier, repaid) if repaid > 0 and confirmation_available else None
        ),
        "supplier_confirmation_available": confirmation_available if total_loans else False,
        "contradictory_declarations": contradictions if total_loans else None,
        "delinquent_loan_count": None,
        "completed_loan_count": None,
        "current_loan_count": None,
    }
    if total_loans and not confirmation_available:
        match_warnings.append(
            "Supplier confirmation is unavailable: relationship_type=SUPPLIER is not a confirmation signal"
        )
    return features, loan_metrics, match_warnings
