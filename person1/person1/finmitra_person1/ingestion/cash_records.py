"""
Cash Records & Self-Declaration Source Adapter.
Handles physical counter cash sales books, receipts, and self-declared unverified income statements.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from ..enums import DataSourceType, TransactionMode
from .base import RawTransactionRecord
from .json_adapter import JsonSourceAdapter
from .csv_adapter import CsvSourceAdapter


class CashRecordsAdapter:
    """Specialized adapter for cash receipts, physical slips, and self-declarations."""

    def __init__(self) -> None:
        self.json_adapter = JsonSourceAdapter()
        self.csv_adapter = CsvSourceAdapter()

    def parse(
        self,
        payload: Any,
        source_id: str,
        source_type: DataSourceType = DataSourceType.CASH_RECORD,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[RawTransactionRecord]:
        if isinstance(payload, str) and ("," in payload or "\n" in payload) and not payload.strip().startswith(("{", "[")):
            raw_records = self.csv_adapter.parse(payload, source_id, source_type, metadata)
        else:
            raw_records = self.json_adapter.parse(payload, source_id, source_type, metadata)

        for rec in raw_records:
            if not rec.raw_mode:
                rec.raw_mode = TransactionMode.CASH.value
            if source_type == DataSourceType.SELF_DECLARATION:
                rec.metadata["is_self_declared"] = True
            elif source_type == DataSourceType.RECEIPT:
                rec.metadata["is_physical_receipt"] = True

        return raw_records
