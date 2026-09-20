"""
Invoice & Supplier Records Source Adapter.
Handles B2B invoices, supplier purchase bills, GST bills, customer delivery slips.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from ..enums import DataSourceType
from .base import RawTransactionRecord
from .json_adapter import JsonSourceAdapter
from .csv_adapter import CsvSourceAdapter


class InvoiceAdapter:
    """Specialized adapter for customer/supplier invoices."""

    def __init__(self) -> None:
        self.json_adapter = JsonSourceAdapter()
        self.csv_adapter = CsvSourceAdapter()

    def parse(
        self,
        payload: Any,
        source_id: str,
        source_type: DataSourceType = DataSourceType.INVOICE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[RawTransactionRecord]:
        if isinstance(payload, str) and ("," in payload or "\n" in payload) and not payload.strip().startswith(("{", "[")):
            raw_records = self.csv_adapter.parse(payload, source_id, source_type, metadata)
        else:
            raw_records = self.json_adapter.parse(payload, source_id, source_type, metadata)

        for rec in raw_records:
            rec.metadata["is_invoice_document"] = True
            # Invoices might have invoice_number in metadata or reference
            inv_no = rec.metadata.get("invoice_number") or rec.metadata.get("invoice_no")
            if inv_no and not rec.raw_reference:
                rec.raw_reference = str(inv_no)

        return raw_records
