"""
Central Transaction Normalization Pipeline.
Transforms heterogeneous RawTransactionRecord objects into canonical NormalizedTransaction objects.
"""
from __future__ import annotations
from typing import List, Tuple, Optional, Dict, Any
from datetime import date
import hashlib
import uuid

from ..enums import (
    TransactionCategory,
    TransactionMode,
    DataSourceType,
    VerificationLevel,
    CategorySource,
    TransactionDirection,
    TransactionStatus,
)
from ..schemas import NormalizedTransaction
from ..ingestion.base import RawTransactionRecord, parse_amount_to_paise, parse_flexible_date
from .provenance import create_provenance
from .categorization import classify_transaction


def normalize_direction(raw_direction: Optional[str]) -> str:
    """Normalize raw direction string into 'CREDIT' or 'DEBIT'."""
    if not raw_direction:
        return "CREDIT"
    d = raw_direction.strip().upper()
    if d in ("CR", "CREDIT", "IN", "DEPOSIT", "RECEIVED", "PAYMENT_RECEIVED", "INCOMING"):
        return "CREDIT"
    if d in ("DR", "DEBIT", "OUT", "WITHDRAWAL", "PAID", "PAYMENT_MADE", "OUTGOING", "EXPENSE"):
        return "DEBIT"
    return "CREDIT"


def normalize_mode(raw_mode: Optional[str], source_type: DataSourceType) -> TransactionMode:
    """Normalize payment mode into standard TransactionMode enum."""
    if not raw_mode:
        if source_type in (DataSourceType.UPI, DataSourceType.QR):
            return TransactionMode.UPI
        if source_type == DataSourceType.POS:
            return TransactionMode.POS
        if source_type == DataSourceType.MARKETPLACE:
            return TransactionMode.MARKETPLACE
        if source_type in (DataSourceType.CASH_RECORD, DataSourceType.RECEIPT, DataSourceType.SELF_DECLARATION):
            return TransactionMode.CASH
        return TransactionMode.BANK_TRANSFER

    m = raw_mode.strip().upper()
    if "UPI" in m or "QR" in m:
        return TransactionMode.UPI
    if "POS" in m or "CARD" in m or "SWIPE" in m:
        return TransactionMode.POS
    if "CASH" in m:
        return TransactionMode.CASH
    if "CHEQUE" in m or "CHQ" in m:
        return TransactionMode.CHEQUE
    if "MARKETPLACE" in m or "ECOMMERCE" in m:
        return TransactionMode.MARKETPLACE
    if "DIRECT" in m or "NACH" in m or "ACH" in m or "MANDATE" in m:
        return TransactionMode.DIRECT_DEBIT
    if "NEFT" in m or "IMPS" in m or "RTGS" in m or "TRANSFER" in m or "BANK" in m:
        return TransactionMode.BANK_TRANSFER

    return TransactionMode.OTHER


def normalize_status(raw_status: Optional[str]) -> TransactionStatus:
    """Normalize transaction execution status."""
    if not raw_status:
        return TransactionStatus.SUCCESS
    s = raw_status.strip().upper()
    if s in ("SUCCESS", "COMPLETED", "SETTLED", "CLEARED", "PAID"):
        return TransactionStatus.SUCCESS
    if s in ("PENDING", "PROCESSING", "IN_PROGRESS", "AUTHORIZED"):
        return TransactionStatus.PENDING
    if s in ("FAILED", "DECLINED", "REJECTED", "BOUNCED"):
        return TransactionStatus.FAILED
    if s in ("REVERSED", "REFUNDED", "CHARGEBACK"):
        return TransactionStatus.REVERSED
    return TransactionStatus.SUCCESS


def normalize_record(
    raw_rec: RawTransactionRecord,
    borrower_name: Optional[str] = None,
    business_name: Optional[str] = None
) -> Tuple[Optional[NormalizedTransaction], Optional[Dict[str, Any]]]:
    """
    Transform a single RawTransactionRecord into a NormalizedTransaction.
    Returns:
        (normalized_transaction, error_dict)
    """
    # 1. Parse date
    parsed_date = parse_flexible_date(raw_rec.raw_date)
    if not parsed_date:
        return None, {
            "record_id": raw_rec.source_record_id,
            "source_id": raw_rec.source_id,
            "source_type": raw_rec.source_type,
            "error": "Invalid or missing date",
            "raw_date": raw_rec.raw_date
        }

    # 2. Parse amount
    amount_paise = parse_amount_to_paise(raw_rec.raw_amount)
    if amount_paise is None or amount_paise < 0:
        return None, {
            "record_id": raw_rec.source_record_id,
            "source_id": raw_rec.source_id,
            "source_type": raw_rec.source_type,
            "error": "Invalid or negative amount",
            "raw_amount": raw_rec.raw_amount
        }

    # 3. Parse direction
    direction = normalize_direction(raw_rec.raw_direction)

    # 4. Parse mode
    mode = normalize_mode(raw_rec.raw_mode, raw_rec.source_type)

    # 5. Parse status
    status = normalize_status(raw_rec.raw_status)

    # 6. Build ID deterministically if source_record_id is missing
    if raw_rec.source_record_id:
        txn_id = raw_rec.source_record_id
    else:
        raw_key = f"{raw_rec.source_id}_{raw_rec.raw_date}_{raw_rec.raw_amount}_{raw_rec.raw_narration}_{raw_rec.raw_index}"
        hash_str = hashlib.md5(raw_key.encode("utf-8")).hexdigest()[:10].upper()
        txn_id = f"TXN-{hash_str}"

    # 7. Classify category and determine verification
    category, cat_conf, cat_source, verification, model_eligible = classify_transaction(
        raw_rec=raw_rec,
        direction=direction,
        amount_paise=amount_paise,
        borrower_name=borrower_name,
        business_name=business_name
    )

    # 8. Build initial provenance record
    prov = create_provenance(raw_rec)

    # 9. Assemble NormalizedTransaction
    meta = raw_rec.metadata.copy() if raw_rec.metadata else {}
    if raw_rec.raw_reference:
        meta["reference"] = raw_rec.raw_reference

    normalized = NormalizedTransaction(
        transaction_id=txn_id,
        date=parsed_date,
        amount_paise=amount_paise,
        direction=direction,
        category=category,
        category_confidence=cat_conf,
        mode=mode,
        source=raw_rec.source_type,
        source_record_id=raw_rec.source_record_id,
        verification=verification,
        category_source=cat_source,
        counterparty_id=None,
        counterparty_name=raw_rec.raw_counterparty,
        narration=raw_rec.raw_narration,
        status=status,
        model_eligible=model_eligible,
        anomaly_flag=False,
        provenance=[prov],
        metadata=meta
    )

    return normalized, None


def normalize_records(
    raw_records: List[RawTransactionRecord],
    borrower_name: Optional[str] = None,
    business_name: Optional[str] = None
) -> Tuple[List[NormalizedTransaction], List[Dict[str, Any]]]:
    """
    Normalize a list of raw records.
    Returns:
        (valid_normalized_transactions, malformed_record_errors)
    """
    valid_txns: List[NormalizedTransaction] = []
    errors: List[Dict[str, Any]] = []

    for raw_rec in raw_records:
        txn, err = normalize_record(raw_rec, borrower_name, business_name)
        if txn is not None:
            valid_txns.append(txn)
        if err is not None:
            errors.append(err)

    return valid_txns, errors
