"""Shared validation helpers for BorrowerInput payloads."""

from __future__ import annotations

from common.schemas import BorrowerInput, Loan, Repayment, Transaction


def validate_borrower_input(profile: BorrowerInput) -> list[str]:
    """Return non-fatal warnings. Invalid amounts are already rejected by schemas."""

    warnings: list[str] = []
    loan_ids = {loan.loan_id for loan in profile.informal_loans}
    tx_ids = {tx.transaction_id for tx in profile.transactions}

    if len(loan_ids) != len(profile.informal_loans):
        warnings.append("Duplicate loan_id values in informal_loans")
    if len(tx_ids) != len(profile.transactions):
        warnings.append("Duplicate transaction_id values in transactions")

    for loan in profile.informal_loans:
        warnings.extend(_loan_warnings(loan))

    for claim in profile.repayment_claims:
        warnings.extend(_repayment_warnings(claim, loan_ids, tx_ids))

    for tx in profile.transactions:
        warnings.extend(_transaction_warnings(tx))

    if profile.cash_flow is not None:
        warnings.append("cash_flow payload is ignored by the repayment engine")

    return warnings


def _loan_warnings(loan: Loan) -> list[str]:
    warnings: list[str] = []
    schedule_fields = (
        loan.installment_amount,
        loan.installment_frequency,
        loan.number_of_installments,
        loan.first_due_date,
    )
    if any(field is None for field in schedule_fields) and not all(
        field is None for field in schedule_fields
    ):
        warnings.append(f"Loan {loan.loan_id} has an incomplete installment schedule")
    return warnings


def _repayment_warnings(
    claim: Repayment, loan_ids: set[str], tx_ids: set[str]
) -> list[str]:
    warnings: list[str] = []
    if claim.loan_id not in loan_ids:
        warnings.append(f"Repayment {claim.repayment_id} references unknown loan_id {claim.loan_id}")
    if claim.transaction_id and claim.transaction_id not in tx_ids:
        warnings.append(
            f"Repayment {claim.repayment_id} references missing transaction_id {claim.transaction_id}"
        )
    return warnings


def _transaction_warnings(tx: Transaction) -> list[str]:
    if tx.direction not in {"CREDIT", "DEBIT"}:
        return [f"Transaction {tx.transaction_id} has invalid direction"]
    return []
