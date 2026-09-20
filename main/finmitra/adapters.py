"""Explicit contract adapters between the four independently built engines."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any

from .schemas import IntegratedBorrowerInput


OPERATING_INFLOW_CATEGORIES = {
    "BUSINESS_INCOME",
    "MARKETPLACE_SETTLEMENT",
    "POS_SETTLEMENT",
    "SUPPORTED_CASH_SALES",
}
VERIFIED_LEVELS = {
    "SOURCE_CONNECTED",
    "CROSS_SOURCE_CORROBORATED",
    "DOCUMENT_MATCHED",
    "LEDGER_MATCHED",
    "MERCHANT_MATCHED",
}


def evidence_payload(profile: IntegratedBorrowerInput) -> dict[str, Any]:
    return {
        "borrower_id": profile.borrower_id,
        "business_name": profile.business_name,
        "sources": profile.sources,
        "metadata": profile.metadata,
    }


def cashflow_payload(
    profile: IntegratedBorrowerInput, evidence_bundle: dict[str, Any]
) -> dict[str, Any]:
    transactions = []
    for txn in evidence_bundle["normalized_transactions"]:
        if txn["amount_paise"] <= 0:
            continue
        transactions.append(
            {
                "transaction_id": txn["transaction_id"],
                "date": txn["date"],
                "amount_paise": txn["amount_paise"],
                "direction": txn["direction"],
                "category": txn["category"],
                "category_confidence": txn["category_confidence"],
                "mode": txn["mode"],
                "source": txn["source"],
                "verification": txn["verification"],
                "category_source": txn["category_source"],
                "counterparty": txn.get("counterparty_id")
                or txn.get("counterparty_name"),
                "status": txn["status"],
                "model_eligible": txn["model_eligible"],
                "balance_after_paise": txn.get("balance_after_paise")
                or txn.get("metadata", {}).get("balance_after_paise"),
                "anomaly_flag": txn.get("anomaly_flag", False),
                # Person 1 emits a list; Person 2 expects a mapping.
                "provenance": {"records": txn.get("provenance", [])},
            }
        )
    return {
        "borrower_id": profile.borrower_id,
        "as_of_date": profile.evaluation_date.isoformat(),
        "transactions": transactions,
    }


def repayment_payload(
    profile: IntegratedBorrowerInput,
    evidence_bundle: dict[str, Any],
    cashflow: dict[str, Any],
) -> dict[str, Any]:
    transactions = []
    aliases: dict[str, str] = {}
    for txn in evidence_bundle["normalized_transactions"]:
        canonical_id = txn["transaction_id"]
        aliases[canonical_id] = canonical_id
        if txn.get("source_record_id"):
            aliases[txn["source_record_id"]] = canonical_id
        for linked_id in txn.get("linked_transaction_ids", []):
            aliases[linked_id] = canonical_id
        transactions.append(
            {
                "transaction_id": canonical_id,
                "date": txn["date"],
                "amount": txn["amount_paise"] / 100.0,
                "direction": txn["direction"],
                "category": txn["category"],
                "counterparty_id": txn.get("counterparty_id")
                or txn.get("counterparty_name"),
                "description": txn.get("narration"),
                "source": txn["source"],
                "verified": txn.get("verification") in VERIFIED_LEVELS,
            }
        )

    claims = []
    for raw in profile.repayment_claims:
        claim = dict(raw)
        transaction_id = claim.get("transaction_id")
        if transaction_id in aliases:
            claim["transaction_id"] = aliases[transaction_id]
        claims.append(claim)

    evidence = evidence_bundle["result"]
    return {
        "borrower_id": profile.borrower_id,
        "evaluation_date": profile.evaluation_date.isoformat(),
        "transactions": transactions,
        "informal_loans": profile.informal_loans,
        "repayment_claims": claims,
        "evidence": {
            "evidence_grade": evidence["evidence_grade"],
            "evidence_confidence": evidence["confidence"],
        },
        "cash_flow": {
            "cash_flow_score": cashflow.get("score"),
            "cash_flow_confidence": cashflow["confidence"],
        },
    }


def capacity_payload(
    profile: IntegratedBorrowerInput,
    evidence_bundle: dict[str, Any],
    cashflow: dict[str, Any],
    repayment: dict[str, Any],
) -> dict[str, Any]:
    context = profile.capacity_context
    features = cashflow["features"]

    # Person 2 works in integer paise. Person 4's capacity contract is INR.
    conservative_inflow = float(
        features.get("conservative_monthly_inflow_paise", 0)
    ) / 100.0
    business_expense = (
        context.essential_business_expense
        if context.essential_business_expense is not None
        else float(features.get("median_monthly_business_expense_paise", 0)) / 100.0
    )
    informal_installments = (
        context.existing_informal_installments
        if context.existing_informal_installments is not None
        else _monthly_informal_installments(profile.informal_loans)
    )
    repayment_features = repayment.get("features", {})
    delinquent = (
        context.outstanding_delinquent_amount
        if context.outstanding_delinquent_amount is not None
        else (
            float(repayment_features.get("outstanding_principal") or 0)
            if repayment.get("new_credit_blocked")
            else 0.0
        )
    )

    result: dict[str, Any] = {
        "conservative_monthly_inflow": round(conservative_inflow, 2),
        "essential_household_expense": context.essential_household_expense,
        "essential_business_expense": round(float(business_expense), 2),
        "existing_formal_emis": context.existing_formal_emis,
        "existing_informal_installments": round(float(informal_installments), 2),
        "income_volatility": min(
            1.0, max(0.0, float(features.get("inflow_volatility") or 0.0))
        ),
        "lowest_recent_monthly_inflow": round(
            _lowest_recent_inflow(
                evidence_bundle["normalized_transactions"],
                profile.evaluation_date,
            ),
            2,
        ),
        "available_balance_buffer": context.available_balance_buffer,
        "outstanding_delinquent_amount": round(float(delinquent), 2),
    }
    if context.requested_loan_amount is not None:
        result.update(
            requested_loan_amount=context.requested_loan_amount,
            annual_interest_rate=context.annual_interest_rate,
            tenure_months=context.tenure_months,
        )
    return result


def _monthly_informal_installments(loans: list[dict[str, Any]]) -> float:
    factors = {"MONTHLY": 1.0, "WEEKLY": 52 / 12, "BIWEEKLY": 26 / 12}
    total = 0.0
    for loan in loans:
        if str(loan.get("declared_status", "")).upper() in {"COMPLETED", "CLOSED", "PAID"}:
            continue
        amount = float(loan.get("installment_amount") or 0)
        total += amount * factors.get(str(loan.get("installment_frequency", "MONTHLY")), 1.0)
    return total


def _lowest_recent_inflow(transactions: list[dict[str, Any]], cutoff: date) -> float:
    months: list[tuple[int, int]] = []
    year, month = cutoff.year, cutoff.month
    for _ in range(6):
        months.append((year, month))
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    totals = {key: 0 for key in months}
    for txn in transactions:
        txn_date = date.fromisoformat(txn["date"])
        key = (txn_date.year, txn_date.month)
        if (
            key in totals
            and txn["direction"] == "CREDIT"
            and txn["status"] == "SUCCESS"
            and txn["model_eligible"]
            and txn["category"] in OPERATING_INFLOW_CATEGORIES
        ):
            totals[key] += int(txn["amount_paise"])
    return min(totals.values(), default=0) / 100.0
