"""Deterministic repayment-to-loan matching. Greedy, not probabilistic."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from common.schemas import BorrowerInput, Loan, Repayment, Transaction
from repayment.models import PaymentMatch
from repayment.schedule import build_full_schedule, expected_installments_as_of

EXPLICIT_LOAN_ID = "EXPLICIT_LOAN_ID"
EXPLICIT_TRANSACTION_REF = "EXPLICIT_TRANSACTION_REF"
COUNTERPARTY_MATCH = "COUNTERPARTY_MATCH"
DATE_PROXIMITY = "DATE_PROXIMITY"
AMOUNT_COMPATIBLE = "AMOUNT_COMPATIBLE"
SELF_DECLARED = "SELF_DECLARED"

DIGITAL_METHODS = {
    EXPLICIT_LOAN_ID,
    EXPLICIT_TRANSACTION_REF,
    COUNTERPARTY_MATCH,
    DATE_PROXIMITY,
    AMOUNT_COMPATIBLE,
}

REPAYMENT_CATEGORIES = {
    "REPAYMENT",
    "LOAN_REPAYMENT",
    "EMI",
    "INSTALLMENT",
    "LOAN_PAYMENT",
}

CONTRADICTORY_CATEGORIES = {
    "SALES",
    "INCOME",
    "DEPOSIT",
    "REFUND",
    "LOAN_DISBURSEMENT",
    "DISBURSEMENT",
    "TRANSFER_IN",
    "SALARY",
    "RENT",
    "PURCHASE",
}

DATE_WINDOW_DAYS = 7
AMOUNT_TOLERANCE = 0.05
LOAN_DATE_GRACE_DAYS = 90

VERIFIED_EXPLICIT_CONFIDENCE = 0.95
UNVERIFIED_EXPLICIT_CONFIDENCE = 0.58
SELF_DECLARED_CONFIDENCE = 0.35


def is_digitally_matched(match: PaymentMatch) -> bool:
    """Linked to an actual transaction. This is not the same as verified evidence."""

    return match.transaction_id is not None and match.match_method in DIGITAL_METHODS


def is_verified_match(match: PaymentMatch) -> bool:
    """Digitally matched and Transaction.verified is True."""

    return is_digitally_matched(match) and match.verified is True


def match_repayments(
    profile: BorrowerInput,
    evaluation_date: Optional[date] = None,
    warnings: Optional[list[str]] = None,
) -> list[PaymentMatch]:
    eval_date = evaluation_date or profile.evaluation_date or date.today()
    loans = {loan.loan_id: loan for loan in profile.informal_loans}
    tx_by_id = {tx.transaction_id: tx for tx in profile.transactions}
    used_tx_ids: set[str] = set()
    matches: list[PaymentMatch] = []
    warning_sink = warnings if warnings is not None else []

    for claim in profile.repayment_claims:
        match = _match_claim(claim, loans, tx_by_id, used_tx_ids, eval_date, warning_sink)
        if match is not None:
            matches.append(match)
            if is_digitally_matched(match) and match.transaction_id:
                used_tx_ids.add(match.transaction_id)

    for loan in profile.informal_loans:
        due_dates = [item.due_date for item in expected_installments_as_of(loan, eval_date)]
        for tx in profile.transactions:
            if tx.transaction_id in used_tx_ids:
                continue
            match = _match_transaction(loan, tx, due_dates, eval_date)
            if match is not None:
                matches.append(match)
                used_tx_ids.add(tx.transaction_id)

    return matches


def _match_claim(
    claim: Repayment,
    loans: dict[str, Loan],
    tx_by_id: dict[str, Transaction],
    used_tx_ids: set[str],
    evaluation_date: date,
    warnings: list[str],
) -> Optional[PaymentMatch]:
    loan = loans.get(claim.loan_id)
    if loan is None:
        return None

    if not claim.transaction_id:
        return _self_declared(claim)

    tx = tx_by_id.get(claim.transaction_id)
    problems = _explicit_transaction_problems(claim, loan, tx, used_tx_ids, evaluation_date)
    if problems:
        warnings.append(
            f"Repayment {claim.repayment_id} transaction_id {claim.transaction_id} "
            f"is not a valid repayment match: {'; '.join(problems)}"
        )
        return _self_declared(claim, contradictory=True)

    assert tx is not None
    evidence_verified = tx.verified is True
    return PaymentMatch(
        repayment_id=claim.repayment_id,
        loan_id=claim.loan_id,
        transaction_id=tx.transaction_id,
        payment_date=tx.date,
        matched_amount=float(claim.amount),
        match_confidence=(
            VERIFIED_EXPLICIT_CONFIDENCE if evidence_verified else UNVERIFIED_EXPLICIT_CONFIDENCE
        ),
        match_method=EXPLICIT_LOAN_ID,
        verified=evidence_verified,
    )


def _explicit_transaction_problems(
    claim: Repayment,
    loan: Loan,
    tx: Optional[Transaction],
    used_tx_ids: set[str],
    evaluation_date: date,
) -> list[str]:
    if tx is None:
        return ["transaction does not exist"]

    problems: list[str] = []
    if tx.transaction_id in used_tx_ids:
        problems.append("transaction is already consumed by another repayment match")
    if tx.amount <= 0:
        problems.append("transaction amount is not positive")
    if tx.direction != "DEBIT":
        problems.append("transaction direction is not borrower-side DEBIT/outflow")
    if not _date_compatible_with_loan(loan, tx.date, evaluation_date):
        problems.append("transaction date is not compatible with the loan")
    if not _claimed_amount_compatible(claim.amount, tx.amount):
        problems.append("claimed repayment amount is not compatible with the transaction amount")
    contradiction = _repayment_contradiction(loan, tx)
    if contradiction:
        problems.append(contradiction)
    return problems


def _match_transaction(
    loan: Loan,
    tx: Transaction,
    due_dates: list[date],
    evaluation_date: date,
) -> Optional[PaymentMatch]:
    """Inferred match. Counterparty/lender equality is never sufficient alone."""

    if tx.amount <= 0 or tx.direction != "DEBIT":
        return None
    if not _date_compatible_with_loan(loan, tx.date, evaluation_date):
        return None
    if _repayment_contradiction(loan, tx):
        return None

    amount_ok = _amount_compatible_with_installment(loan, tx.amount)
    date_ok = any(abs((tx.date - due).days) <= DATE_WINDOW_DAYS for due in due_dates)
    looks_like_repayment = (tx.category or "").upper() in REPAYMENT_CATEGORIES
    counterparty_ok = bool(
        tx.counterparty_id and loan.lender_id and tx.counterparty_id == loan.lender_id
    )
    evidence_verified = tx.verified is True

    if looks_like_repayment and counterparty_ok and amount_ok and date_ok:
        return _inferred_match(
            loan, tx, COUNTERPARTY_MATCH, 0.80 if evidence_verified else 0.55, evidence_verified
        )
    if looks_like_repayment and amount_ok and date_ok:
        return _inferred_match(
            loan, tx, DATE_PROXIMITY, 0.70 if evidence_verified else 0.50, evidence_verified
        )
    if counterparty_ok and amount_ok and date_ok:
        return _inferred_match(
            loan, tx, AMOUNT_COMPATIBLE, 0.55 if evidence_verified else 0.45, evidence_verified
        )
    return None


def _inferred_match(
    loan: Loan, tx: Transaction, method: str, confidence: float, verified: bool
) -> PaymentMatch:
    return PaymentMatch(
        repayment_id=f"MATCH-{tx.transaction_id}",
        loan_id=loan.loan_id,
        transaction_id=tx.transaction_id,
        payment_date=tx.date,
        matched_amount=float(tx.amount),
        match_confidence=confidence,
        match_method=method,
        verified=verified,
    )


def _self_declared(claim: Repayment, contradictory: bool = False) -> PaymentMatch:
    return PaymentMatch(
        repayment_id=claim.repayment_id,
        loan_id=claim.loan_id,
        transaction_id=None,
        payment_date=claim.date,
        matched_amount=float(claim.amount),
        match_confidence=SELF_DECLARED_CONFIDENCE,
        match_method=SELF_DECLARED,
        verified=False,
        contradictory=contradictory,
    )


def _claimed_amount_compatible(claimed_amount: float, tx_amount: float) -> bool:
    if claimed_amount <= 0 or tx_amount <= 0:
        return False
    baseline = max(claimed_amount, tx_amount)
    return abs(claimed_amount - tx_amount) / baseline <= AMOUNT_TOLERANCE


def _amount_compatible_with_installment(loan: Loan, amount: float) -> bool:
    if not loan.installment_amount:
        return False
    expected = float(loan.installment_amount)
    if expected <= 0 or amount <= 0:
        return False
    return abs(amount - expected) / expected <= AMOUNT_TOLERANCE


def _date_compatible_with_loan(loan: Loan, tx_date: date, evaluation_date: date) -> bool:
    if tx_date < loan.issue_date:
        return False
    full_schedule = build_full_schedule(loan)
    if full_schedule:
        last_due = full_schedule[-1].due_date
        if tx_date > last_due + timedelta(days=LOAN_DATE_GRACE_DAYS):
            return False
        return True
    return tx_date <= evaluation_date


def _repayment_contradiction(loan: Loan, tx: Transaction) -> Optional[str]:
    category = (tx.category or "").upper()
    if category in CONTRADICTORY_CATEGORIES:
        return "transaction category contradicts a repayment"
    if loan.lender_id and tx.counterparty_id and tx.counterparty_id != loan.lender_id:
        return "transaction counterparty contradicts the loan lender"
    description = (tx.description or "").lower()
    if any(token in description for token in ("disbursement", "loan received", "loan credit")):
        return "transaction description contradicts a repayment"
    return None
