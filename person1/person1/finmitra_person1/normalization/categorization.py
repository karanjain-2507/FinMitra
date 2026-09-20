"""
Explainable Transaction Categorization Engine.
Deterministic, rule-based classification assigning categories, sources,
verification levels, and confidence scores based on concrete evidence.
"""
from __future__ import annotations
import re
from typing import Optional, Tuple, Dict, Any

from ..enums import (
    TransactionCategory,
    TransactionMode,
    DataSourceType,
    VerificationLevel,
    CategorySource,
    TransactionDirection,
)
from ..ingestion.base import RawTransactionRecord
from ..config import (
    CONFIDENCE_MERCHANT_QR,
    CONFIDENCE_POS_SETTLEMENT,
    CONFIDENCE_INVOICE_MATCH,
    CONFIDENCE_LEDGER_MATCH,
    CONFIDENCE_MARKETPLACE,
    CONFIDENCE_COUNTERPARTY_PATTERN,
    CONFIDENCE_NARRATION_RULE,
    CONFIDENCE_SELF_DECLARED,
    CONFIDENCE_UNCLASSIFIED,
)
from .transfers import evaluate_transfer


# Keyword catalogues for deterministic categorization
SUPPLIER_KEYWORDS = [
    r"\bsupplier\b", r"\bdistributor\b", r"\bwholesal(?:e|er)\b",
    r"\bstock\b", r"\binventory\b", r"\btrader\b", r"\bagencies\b",
    r"\bseeds\b", r"\bfertilizer\b", r"\bpesticide\b", r"\bgoods\b",
    r"\braw\s*material\b"
]

RENT_UTILITY_KEYWORDS = [
    r"\brent\b", r"\belectricity\b", r"\bpower\b", r"\bwater\s*bill\b",
    r"\bgas\b", r"\binternet\b", r"\bbroadband\b", r"\btelecom\b"
]

TAX_FEE_KEYWORDS = [
    r"\bgst\b", r"\btax\b", r"\btds\b", r"\bchallan\b",
    r"\bannual\s*fee\b", r"\bcharge\b", r"\bpenalty\b", r"\bmdr\b"
]

LOAN_KEYWORDS = [
    r"\bloan\b", r"\bemi\b", r"\bdisburs(?:al|ement)\b", r"\bfinance\b",
    r"\bfintech\b", r"\bnbfc\b", r"\bkred\b", r"\bcredit\s*society\b"
]

INFORMAL_LOAN_KEYWORDS = [
    r"\bvyaj\b", r"\binterest\b", r"\bcommittee\b", r"\bbisi\b",
    r"\bchit\s*fund\b", r"\blocal\s*lender\b", r"\bhawala\b", r"\bkarza\b",
    r"\budhari\b", r"\bborrowed\b"
]

MARKETPLACE_NAMES = [
    r"\bamazon\b", r"\bflipkart\b", r"\bswiggy\b", r"\bzomato\b",
    r"\bmeesho\b", r"\bblinkit\b", r"\bzepto\b", r"\binstamart\b",
    r"\bondc\b", r"\bmyntra\b"
]


def classify_transaction(
    raw_rec: RawTransactionRecord,
    direction: str,
    amount_paise: int,
    borrower_name: Optional[str] = None,
    business_name: Optional[str] = None,
) -> Tuple[TransactionCategory, float, CategorySource, VerificationLevel, bool]:
    """
    Deterministically classify a transaction and assign confidence & verification.

    Returns:
        (category, category_confidence, category_source, verification_level, model_eligible)
    """
    narration = (raw_rec.raw_narration or "").strip()
    counterparty = (raw_rec.raw_counterparty or "").strip()
    meta = raw_rec.metadata or {}
    source_type = raw_rec.source_type
    n_lower = narration.lower()
    c_lower = counterparty.lower()

    # 1. Check for Self-Declared Cash Income
    if (
        source_type == DataSourceType.SELF_DECLARATION
        or meta.get("is_self_declared") is True
        or raw_rec.raw_category == "SELF_DECLARED_CASH_INCOME"
    ):
        return (
            TransactionCategory.SELF_DECLARED_CASH_INCOME,
            CONFIDENCE_SELF_DECLARED,
            CategorySource.SELF_DECLARED,
            VerificationLevel.SELF_DECLARED,
            False  # Strictly model_eligible = False until corroborated
        )

    # 2. Check for Internal Transfers & Own-Account Movements
    is_trf, trf_cat, trf_src, trf_conf = evaluate_transfer(
        narration=narration,
        counterparty=counterparty,
        borrower_name=borrower_name,
        business_name=business_name
    )
    if is_trf and trf_cat and trf_src and trf_conf:
        return (
            trf_cat,
            trf_conf,
            trf_src,
            VerificationLevel.SOURCE_CONNECTED,
            False  # Transfers excluded from revenue/expense models
        )

    # 3. Check for Marketplace Payouts / Settlements
    if source_type == DataSourceType.MARKETPLACE or any(re.search(p, n_lower) or re.search(p, c_lower) for p in MARKETPLACE_NAMES):
        if direction == "CREDIT":
            return (
                TransactionCategory.MARKETPLACE_SETTLEMENT,
                CONFIDENCE_MARKETPLACE,
                CategorySource.MARKETPLACE_SETTLEMENT,
                VerificationLevel.SOURCE_CONNECTED,
                True
            )

    # 4. Check for POS Merchant Settlements
    if (
        source_type == DataSourceType.POS
        or meta.get("is_pos_settlement") is True
        or "pos settlement" in n_lower
        or "edc batch" in n_lower
    ):
        if direction == "CREDIT":
            return (
                TransactionCategory.POS_SETTLEMENT,
                CONFIDENCE_POS_SETTLEMENT,
                CategorySource.POS_MERCHANT_MATCH,
                VerificationLevel.MERCHANT_MATCHED,
                True
            )

    # 5. Check for Registered Merchant QR / Merchant VPA
    if (
        source_type == DataSourceType.QR
        or meta.get("qr_collection") is True
        or meta.get("is_merchant_qr") is True
        or ".merchant@" in c_lower
        or "@merchant" in c_lower
        or meta.get("merchant_id") is not None
    ):
        if direction == "CREDIT":
            return (
                TransactionCategory.BUSINESS_INCOME,
                CONFIDENCE_MERCHANT_QR,
                CategorySource.MERCHANT_QR_MATCH,
                VerificationLevel.MERCHANT_MATCHED,
                True
            )

    # 6. Check for Invoice-Supported Transactions
    if (
        source_type in (DataSourceType.INVOICE, DataSourceType.SUPPLIER_RECORD)
        or meta.get("is_invoice_document") is True
        or meta.get("invoice_id") is not None
        or meta.get("invoice_matched") is True
    ):
        if direction == "CREDIT":
            return (
                TransactionCategory.BUSINESS_INCOME,
                CONFIDENCE_INVOICE_MATCH,
                CategorySource.INVOICE_MATCH,
                VerificationLevel.DOCUMENT_MATCHED,
                True
            )
        else:
            return (
                TransactionCategory.BUSINESS_EXPENSE,
                CONFIDENCE_INVOICE_MATCH,
                CategorySource.INVOICE_MATCH,
                VerificationLevel.DOCUMENT_MATCHED,
                True
            )

    # 7. Check for Digital Ledger Records
    if source_type == DataSourceType.BUSINESS_LEDGER or meta.get("is_ledger_record") is True:
        if direction == "CREDIT":
            return (
                TransactionCategory.BUSINESS_INCOME,
                CONFIDENCE_LEDGER_MATCH,
                CategorySource.LEDGER_MATCH,
                VerificationLevel.LEDGER_MATCHED,
                True
            )
        else:
            return (
                TransactionCategory.BUSINESS_EXPENSE,
                CONFIDENCE_LEDGER_MATCH,
                CategorySource.LEDGER_MATCH,
                VerificationLevel.LEDGER_MATCHED,
                True
            )

    # 8. Check for Physical Receipts (Document-backed cash/retail)
    if source_type == DataSourceType.RECEIPT or meta.get("is_physical_receipt") is True:
        if direction == "CREDIT":
            return (
                TransactionCategory.BUSINESS_INCOME,
                0.85,
                CategorySource.INVOICE_MATCH,
                VerificationLevel.DOCUMENT_MATCHED,
                True
            )
        else:
            return (
                TransactionCategory.BUSINESS_EXPENSE,
                0.85,
                CategorySource.INVOICE_MATCH,
                VerificationLevel.DOCUMENT_MATCHED,
                True
            )

    # 9. Check for Cash Deposits and Cash Withdrawals
    if (
        "cash deposit" in n_lower
        or "atm deposit" in n_lower
        or "by cash" in n_lower
        or (raw_rec.raw_mode == "CASH" and direction == "CREDIT" and source_type == DataSourceType.BANK_STATEMENT)
    ):
        # Uncorroborated cash deposit into bank is NOT automatically verified business income
        return (
            TransactionCategory.CASH_DEPOSIT,
            0.85,
            CategorySource.NARRATION_RULE,
            VerificationLevel.SOURCE_CONNECTED,
            False
        )

    if (
        "cash withdrawal" in n_lower
        or "atm wdl" in n_lower
        or "atm cash" in n_lower
        or (raw_rec.raw_mode == "CASH" and direction == "DEBIT")
    ):
        return (
            TransactionCategory.CASH_WITHDRAWAL,
            0.85,
            CategorySource.NARRATION_RULE,
            VerificationLevel.SOURCE_CONNECTED,
            True
        )

    # 10. Check for Informal Loan Records
    if any(re.search(p, n_lower) or re.search(p, c_lower) for p in INFORMAL_LOAN_KEYWORDS):
        return (
            TransactionCategory.INFORMAL_LOAN,
            0.80,
            CategorySource.NARRATION_RULE,
            VerificationLevel.SOURCE_CONNECTED if source_type == DataSourceType.BANK_STATEMENT else VerificationLevel.UNVERIFIED,
            True  # Preserved for Person 3 obligation analysis
        )

    # 11. Check for Formal Loan Disbursements and Repayments
    if any(re.search(p, n_lower) or re.search(p, c_lower) for p in LOAN_KEYWORDS):
        if direction == "CREDIT":
            return (
                TransactionCategory.LOAN_DISBURSEMENT,
                0.85,
                CategorySource.NARRATION_RULE,
                VerificationLevel.SOURCE_CONNECTED,
                True
            )
        else:
            return (
                TransactionCategory.LOAN_REPAYMENT,
                0.85,
                CategorySource.NARRATION_RULE,
                VerificationLevel.SOURCE_CONNECTED,
                True
            )

    # 12. Check for Taxes and Bank/Platform Fees
    if any(re.search(p, n_lower) for p in TAX_FEE_KEYWORDS):
        if "gst" in n_lower or "tax" in n_lower or "tds" in n_lower:
            return (
                TransactionCategory.TAX,
                0.85,
                CategorySource.NARRATION_RULE,
                VerificationLevel.SOURCE_CONNECTED,
                True
            )
        else:
            return (
                TransactionCategory.FEE,
                0.85,
                CategorySource.NARRATION_RULE,
                VerificationLevel.SOURCE_CONNECTED,
                True
            )

    # 13. Check for Supplier and Inventory Debits
    if direction == "DEBIT" and any(re.search(p, n_lower) or re.search(p, c_lower) for p in SUPPLIER_KEYWORDS):
        return (
            TransactionCategory.BUSINESS_EXPENSE,
            0.75,
            CategorySource.COUNTERPARTY_PATTERN,
            VerificationLevel.SOURCE_CONNECTED,
            True
        )

    # 14. Check for Rent / Utility Debits
    if direction == "DEBIT" and any(re.search(p, n_lower) for p in RENT_UTILITY_KEYWORDS):
        return (
            TransactionCategory.BUSINESS_EXPENSE,
            0.75,
            CategorySource.NARRATION_RULE,
            VerificationLevel.SOURCE_CONNECTED,
            True
        )

    # 15. Check for Refunds and Reversals
    if "refund" in n_lower or "reversal" in n_lower or "cashback" in n_lower or "return credit" in n_lower:
        return (
            TransactionCategory.REFUND,
            0.85,
            CategorySource.NARRATION_RULE,
            VerificationLevel.SOURCE_CONNECTED,
            False  # Refunds should not falsely inflate revenue
        )

    # 16. Check for Household and Domestic Expenses
    if direction == "DEBIT" and ("school" in n_lower or "tuition" in n_lower or "grocery" in n_lower or "supermarket" in n_lower or "medical" in n_lower or "hospital" in n_lower or "personal" in n_lower):
        return (
            TransactionCategory.HOUSEHOLD_EXPENSE,
            0.80,
            CategorySource.NARRATION_RULE,
            VerificationLevel.SOURCE_CONNECTED,
            False  # Household expenses excluded from business model eligibility
        )

    # 17. Check for Savings and Investments
    if "mutual fund" in n_lower or "sip" in n_lower or "fixed deposit" in n_lower or "fd " in n_lower or "ppf" in n_lower or "rd deposit" in n_lower:
        return (
            TransactionCategory.SAVINGS,
            0.85,
            CategorySource.NARRATION_RULE,
            VerificationLevel.SOURCE_CONNECTED,
            False
        )

    # 18. Recurring Customer Payment Pattern (if tagged in metadata)
    if meta.get("is_recurring_customer") is True and direction == "CREDIT":
        return (
            TransactionCategory.BUSINESS_INCOME,
            CONFIDENCE_COUNTERPARTY_PATTERN,
            CategorySource.COUNTERPARTY_PATTERN,
            VerificationLevel.SOURCE_CONNECTED,
            True
        )

    # 16. Fallback / Weak Evidence: UNCLASSIFIED
    # Do NOT invent business income certainty for generic credits
    verification_fallback = VerificationLevel.SOURCE_CONNECTED if source_type == DataSourceType.BANK_STATEMENT else VerificationLevel.UNVERIFIED
    return (
        TransactionCategory.UNCLASSIFIED,
        CONFIDENCE_UNCLASSIFIED,
        CategorySource.NONE,
        verification_fallback,
        False  # Ambiguous unclassified transactions should not feed predictive model directly
    )
