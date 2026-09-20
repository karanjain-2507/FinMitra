"""
POS (Point of Sale) Source Adapter.
Handles EDC machine swipes, card settlements, terminal reports.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from ..enums import DataSourceType, TransactionMode
from .base import RawTransactionRecord
from .json_adapter import JsonSourceAdapter
from .csv_adapter import CsvSourceAdapter


class PosAdapter:
    """Specialized adapter for POS terminal records."""

    def __init__(self) -> None:
        self.json_adapter = JsonSourceAdapter()
        self.csv_adapter = CsvSourceAdapter()

    def parse(
        self,
        payload: Any,
        source_id: str,
        source_type: DataSourceType = DataSourceType.POS,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[RawTransactionRecord]:
        if isinstance(payload, str) and ("," in payload or "\n" in payload) and not payload.strip().startswith(("{", "[")):
            raw_records = self.csv_adapter.parse(payload, source_id, source_type, metadata)
        else:
            raw_records = self.json_adapter.parse(payload, source_id, source_type, metadata)

        for rec in raw_records:
            if not rec.raw_mode:
                rec.raw_mode = TransactionMode.POS.value
            rec.metadata["is_pos_settlement"] = True

        return raw_records
