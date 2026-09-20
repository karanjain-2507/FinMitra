"""
Canonical Enums for FinMitra Person 1 (Evidence Engine + Ingestion + Normalization).
All enums are string enums for clean JSON serialization and interoperability.
"""
from __future__ import annotations
from enum import Enum


class TransactionCategory(str, Enum):
    """Normalized category of financial transaction."""
    BUSINESS_INCOME = "BUSINESS_INCOME"
    BUSINESS_EXPENSE = "BUSINESS_EXPENSE"
    HOUSEHOLD_EXPENSE = "HOUSEHOLD_EXPENSE"
    TRANSFER = "TRANSFER"
    LOAN_DISBURSEMENT = "LOAN_DISBURSEMENT"
    LOAN_REPAYMENT = "LOAN_REPAYMENT"
    INFORMAL_LOAN = "INFORMAL_LOAN"
    MARKETPLACE_SETTLEMENT = "MARKETPLACE_SETTLEMENT"
    POS_SETTLEMENT = "POS_SETTLEMENT"
    CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"
    FEE = "FEE"
    TAX = "TAX"
    REFUND = "REFUND"
    SAVINGS = "SAVINGS"
    SELF_DECLARED_CASH_INCOME = "SELF_DECLARED_CASH_INCOME"
    UNCLASSIFIED = "UNCLASSIFIED"
    OTHER = "OTHER"


class TransactionMode(str, Enum):
    """Payment mode / rail through which transaction occurred."""
    BANK_TRANSFER = "BANK_TRANSFER"
    UPI = "UPI"
    POS = "POS"
    CARD = "CARD"
    MARKETPLACE = "MARKETPLACE"
    CASH = "CASH"
    CHEQUE = "CHEQUE"
    DIRECT_DEBIT = "DIRECT_DEBIT"
    OTHER = "OTHER"


class DataSourceType(str, Enum):
    """Originating source type of the transaction data."""
    BANK_STATEMENT = "BANK_STATEMENT"
    UPI = "UPI"
    QR = "QR"
    POS = "POS"
    MARKETPLACE = "MARKETPLACE"
    BUSINESS_LEDGER = "BUSINESS_LEDGER"
    INVOICE = "INVOICE"
    SUPPLIER_RECORD = "SUPPLIER_RECORD"
    RECEIPT = "RECEIPT"
    CASH_RECORD = "CASH_RECORD"
    SELF_DECLARATION = "SELF_DECLARATION"
    OTHER = "OTHER"


class VerificationLevel(str, Enum):
    """
    Evidence verification status.
    NOTE: SOURCE_CONNECTED does not mean factual business truth;
    it means record originates from a connected financial account.
    """
    SOURCE_CONNECTED = "SOURCE_CONNECTED"
    CROSS_SOURCE_CORROBORATED = "CROSS_SOURCE_CORROBORATED"
    DOCUMENT_MATCHED = "DOCUMENT_MATCHED"
    LEDGER_MATCHED = "LEDGER_MATCHED"
    MERCHANT_MATCHED = "MERCHANT_MATCHED"
    SELF_DECLARED = "SELF_DECLARED"
    UNVERIFIED = "UNVERIFIED"


class CategorySource(str, Enum):
    """Explanation of how the transaction category was established."""
    MERCHANT_QR_MATCH = "MERCHANT_QR_MATCH"
    POS_MERCHANT_MATCH = "POS_MERCHANT_MATCH"
    INVOICE_MATCH = "INVOICE_MATCH"
    LEDGER_MATCH = "LEDGER_MATCH"
    MARKETPLACE_SETTLEMENT = "MARKETPLACE_SETTLEMENT"
    COUNTERPARTY_PATTERN = "COUNTERPARTY_PATTERN"
    NARRATION_RULE = "NARRATION_RULE"
    CROSS_SOURCE_MATCH = "CROSS_SOURCE_MATCH"
    SELF_DECLARED = "SELF_DECLARED"
    NONE = "NONE"


class TransactionDirection(str, Enum):
    """Flow of money relative to the borrower's account/record."""
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class TransactionStatus(str, Enum):
    """Execution status of the transaction."""
    SUCCESS = "SUCCESS"
    PENDING = "PENDING"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class EvidenceGrade(str, Enum):
    """Overall evidence quality grade."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class EvidenceStatus(str, Enum):
    """Lifecycle status of the evidence assessment."""
    SUFFICIENT = "SUFFICIENT"
    DEGRADED = "DEGRADED"
    INSUFFICIENT = "INSUFFICIENT"


class ReasonDirection(str, Enum):
    """Directional impact of a reason code on evidence assessment."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class ConflictType(str, Enum):
    """Type of cross-source or internal data conflict detected."""
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DATE_MISMATCH = "DATE_MISMATCH"
    DIRECTION_MISMATCH = "DIRECTION_MISMATCH"
    STATUS_MISMATCH = "STATUS_MISMATCH"
    DUPLICATE_ID = "DUPLICATE_ID"
    UNKNOWN = "UNKNOWN"


class ConflictSeverity(str, Enum):
    """Severity of a detected conflict."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
