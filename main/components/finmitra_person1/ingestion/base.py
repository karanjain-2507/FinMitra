"""
Base classes and utilities for data ingestion.
Defines RawTransactionRecord and SourceAdapter protocol.
"""
from __future__ import annotations
import re
from typing import Protocol, runtime_checkable, Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, date

from ..enums import DataSourceType


@dataclass
class RawTransactionRecord:
    """
    Intermediate representation of a raw financial transaction record
    before formal normalization, validation, and categorization.
    """
    source_type: DataSourceType
    source_id: str
    source_record_id: Optional[str]
    raw_date: Any
    raw_amount: Any
    raw_direction: Optional[str] = None  # e.g., 'CR', 'DR', 'CREDIT', 'DEBIT', 'IN', 'OUT'
    raw_mode: Optional[str] = None       # e.g., 'UPI', 'NEFT', 'IMPS', 'POS', 'CASH'
    raw_narration: Optional[str] = None
    raw_counterparty: Optional[str] = None
    raw_reference: Optional[str] = None  # UTR, Invoice No, Transaction Ref
    raw_status: Optional[str] = None
    raw_category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_index: Optional[int] = None


@runtime_checkable
class SourceAdapter(Protocol):
    """Protocol defining interface for source-specific record adapters."""

    def parse(
        self,
        payload: Any,
        source_id: str,
        source_type: DataSourceType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[RawTransactionRecord]:
        """Parse raw source payload into list of RawTransactionRecords."""
        ...


def parse_amount_to_paise(raw_amount: Any) -> Optional[int]:
    """
    Robustly convert various raw amount representations into integer paise.
    Handles:
    - 1850 (assumed rupees if float/int < 1,000,000 without paise tag, or checked)
    - "₹1,850.50" -> 185050 paise
    - "1850.50" -> 185050 paise
    - "1850" -> 185000 paise (if rupees string)
    - integer paise if explicitly flagged in metadata
    """
    if raw_amount is None:
        return None

    if isinstance(raw_amount, (int, float)):
        # If float with decimals or standard integer rupees
        # Round carefully to avoid floating point imprecision
        return int(round(float(raw_amount) * 100))

    if isinstance(raw_amount, str):
        cleaned = raw_amount.strip()
        if not cleaned:
            return None
        # Remove currency symbols, commas, whitespace
        cleaned = re.sub(r"[₹$,\s]", "", cleaned)
        try:
            val = float(cleaned)
            return int(round(val * 100))
        except ValueError:
            return None

    return None


def parse_flexible_date(raw_date: Any) -> Optional[date]:
    """
    Parse multiple date formats into a standard datetime.date.
    Supports ISO (YYYY-MM-DD), Indian formats (DD/MM/YYYY, DD-MM-YYYY), timestamps.
    """
    if raw_date is None:
        return None

    if isinstance(raw_date, date):
        return raw_date

    if isinstance(raw_date, datetime):
        return raw_date.date()

    if isinstance(raw_date, str):
        cleaned = raw_date.strip()
        if not cleaned:
            return None

        # Common formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d-%b-%Y",
            "%d %b %Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue

        # Try regex extraction for YYYY-MM-DD
        iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", cleaned)
        if iso_match:
            try:
                return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
            except ValueError:
                pass

        # Try regex extraction for DD/MM/YYYY or DD-MM-YYYY
        dmy_match = re.search(r"(\d{2})[/-](\d{2})[/-](\d{4})", cleaned)
        if dmy_match:
            try:
                return date(int(dmy_match.group(3)), int(dmy_match.group(2)), int(dmy_match.group(1)))
            except ValueError:
                pass

    return None
