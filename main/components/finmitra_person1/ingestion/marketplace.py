"""
Marketplace / E-Commerce Source Adapter.
Handles Swiggy, Zomato, Amazon, Flipkart, ONDC, Meesho merchant settlements.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from ..enums import DataSourceType, TransactionMode
from .base import RawTransactionRecord
from .json_adapter import JsonSourceAdapter
from .csv_adapter import CsvSourceAdapter


class MarketplaceAdapter:
    """Specialized adapter for marketplace platform settlements."""

    def __init__(self) -> None:
        self.json_adapter = JsonSourceAdapter()
        self.csv_adapter = CsvSourceAdapter()

    def parse(
        self,
        payload: Any,
        source_id: str,
        source_type: DataSourceType = DataSourceType.MARKETPLACE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[RawTransactionRecord]:
        if isinstance(payload, str) and ("," in payload or "\n" in payload) and not payload.strip().startswith(("{", "[")):
            raw_records = self.csv_adapter.parse(payload, source_id, source_type, metadata)
        else:
            raw_records = self.json_adapter.parse(payload, source_id, source_type, metadata)

        for rec in raw_records:
            if not rec.raw_mode:
                rec.raw_mode = TransactionMode.MARKETPLACE.value
            rec.metadata["is_marketplace_settlement"] = True

        return raw_records
