"""
Bank Statement Source Adapter.
Handles parsing and domain-specific extraction for bank accounts (Savings/Current).
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import re

from ..enums import DataSourceType, TransactionMode
from .base import RawTransactionRecord
from .json_adapter import JsonSourceAdapter
from .csv_adapter import CsvSourceAdapter


class BankStatementAdapter:
    """Specialized adapter for bank statements."""

    def __init__(self) -> None:
        self.json_adapter = JsonSourceAdapter()
        self.csv_adapter = CsvSourceAdapter()

    def parse(
        self,
        payload: Any,
        source_id: str,
        source_type: DataSourceType = DataSourceType.BANK_STATEMENT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[RawTransactionRecord]:
        if isinstance(payload, str) and ("," in payload or "\n" in payload) and not payload.strip().startswith(("{", "[")):
            raw_records = self.csv_adapter.parse(payload, source_id, source_type, metadata)
        else:
            raw_records = self.json_adapter.parse(payload, source_id, source_type, metadata)

        # Enrich with bank statement domain heuristics
        for rec in raw_records:
            narration = rec.raw_narration or ""
            # Detect mode from narration if not set
            if not rec.raw_mode:
                if "UPI/" in narration or "/UPI/" in narration or narration.startswith("UPI"):
                    rec.raw_mode = TransactionMode.UPI.value
                elif "NEFT" in narration:
                    rec.raw_mode = TransactionMode.BANK_TRANSFER.value
                elif "IMPS" in narration:
                    rec.raw_mode = TransactionMode.BANK_TRANSFER.value
                elif "RTGS" in narration:
                    rec.raw_mode = TransactionMode.BANK_TRANSFER.value
                elif "POS " in narration or "POS/" in narration or "EDC" in narration:
                    rec.raw_mode = TransactionMode.POS.value
                elif "ATM" in narration or "CASH DEP" in narration or "CASH WDL" in narration:
                    rec.raw_mode = TransactionMode.CASH.value
                elif "CHQ" in narration or "CHEQUE" in narration:
                    rec.raw_mode = TransactionMode.CHEQUE.value
                elif "ACH/" in narration or "NACH/" in narration or "ECS/" in narration:
                    rec.raw_mode = TransactionMode.DIRECT_DEBIT.value

            # Extract UTR or Reference from narration if reference is missing
            if not rec.raw_reference and narration:
                utr_match = re.search(r"(?:UPI|NEFT|IMPS|REF)[/:]([A-Za-z0-9]+)", narration)
                if utr_match:
                    rec.raw_reference = utr_match.group(1)

        return raw_records
