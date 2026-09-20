"""
UPI & QR Source Adapter.
Handles UPI collections, QR merchant settlements, VPA payments.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from ..enums import DataSourceType, TransactionMode
from .base import RawTransactionRecord
from .json_adapter import JsonSourceAdapter
from .csv_adapter import CsvSourceAdapter


class UpiAdapter:
    """Specialized adapter for UPI and QR payments."""

    def __init__(self) -> None:
        self.json_adapter = JsonSourceAdapter()
        self.csv_adapter = CsvSourceAdapter()

    def parse(
        self,
        payload: Any,
        source_id: str,
        source_type: DataSourceType = DataSourceType.UPI,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[RawTransactionRecord]:
        if isinstance(payload, str) and ("," in payload or "\n" in payload) and not payload.strip().startswith(("{", "[")):
            raw_records = self.csv_adapter.parse(payload, source_id, source_type, metadata)
        else:
            raw_records = self.json_adapter.parse(payload, source_id, source_type, metadata)

        for rec in raw_records:
            if not rec.raw_mode:
                rec.raw_mode = TransactionMode.UPI.value
            # Tag QR collections
            if source_type == DataSourceType.QR or (rec.metadata and rec.metadata.get("is_qr")):
                rec.metadata["qr_collection"] = True

        return raw_records
