"""
Generic JSON source adapter.
Extracts raw transaction dictionaries from JSON arrays or objects.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import json

from ..enums import DataSourceType
from .base import RawTransactionRecord, SourceAdapter


class JsonSourceAdapter:
    """Parses JSON-based payloads into list of RawTransactionRecords."""

    def parse(
        self,
        payload: Any,
        source_id: str,
        source_type: DataSourceType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[RawTransactionRecord]:
        records: List[RawTransactionRecord] = []
        meta = metadata or {}

        # If payload is a string JSON, parse it
        data = payload
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except Exception:
                # Store unparseable payload as single malformed record
                return [
                    RawTransactionRecord(
                        source_type=source_type,
                        source_id=source_id,
                        source_record_id=None,
                        raw_date=None,
                        raw_amount=None,
                        metadata={"raw_error": "Invalid JSON string", "payload": payload}
                    )
                ]

        # Extract items list
        items: List[Dict[str, Any]] = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if "records" in data and isinstance(data["records"], list):
                items = data["records"]
            elif "transactions" in data and isinstance(data["transactions"], list):
                items = data["transactions"]
            elif "entries" in data and isinstance(data["entries"], list):
                items = data["entries"]
            else:
                items = [data]

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                records.append(
                    RawTransactionRecord(
                        source_type=source_type,
                        source_id=source_id,
                        source_record_id=f"ITEM-{idx}",
                        raw_date=None,
                        raw_amount=None,
                        metadata={"raw_data": item, "raw_error": "Non-dictionary item"},
                        raw_index=idx
                    )
                )
                continue

            # Extract fields with multiple possible key aliases
            rec_id = (
                item.get("id")
                or item.get("transaction_id")
                or item.get("txn_id")
                or item.get("record_id")
                or item.get("ref_no")
                or f"REC-{idx+1}"
            )
            raw_date = (
                item.get("date")
                or item.get("txn_date")
                or item.get("transaction_date")
                or item.get("timestamp")
                or item.get("value_date")
            )
            # Check amount vs amount_paise
            if "amount_paise" in item:
                # If already in paise, convert to rupees representation or pass directly
                raw_amount = item.get("amount_paise") / 100.0 if isinstance(item.get("amount_paise"), (int, float)) else item.get("amount_paise")
            else:
                raw_amount = (
                    item.get("amount")
                    or item.get("txn_amount")
                    or item.get("value")
                    or item.get("total_amount")
                )

            raw_dir = (
                item.get("direction")
                or item.get("type")
                or item.get("txn_type")
                or item.get("dr_cr")
            )
            raw_narration = (
                item.get("narration")
                or item.get("description")
                or item.get("remarks")
                or item.get("note")
                or item.get("details")
            )
            raw_counterparty = (
                item.get("counterparty")
                or item.get("counterparty_name")
                or item.get("payer")
                or item.get("payee")
                or item.get("vpa")
                or item.get("merchant_name")
            )
            raw_reference = (
                item.get("reference")
                or item.get("ref_no")
                or item.get("utr")
                or item.get("invoice_id")
                or item.get("order_id")
                or item.get("batch_id")
            )
            raw_mode = item.get("mode") or item.get("payment_mode") or item.get("channel")
            raw_status = item.get("status") or item.get("state")
            raw_category = item.get("category") or item.get("tag")

            # Collect remaining metadata
            item_meta = {**meta, **{k: v for k, v in item.items() if k not in {
                "id", "transaction_id", "txn_id", "record_id", "date", "txn_date",
                "transaction_date", "timestamp", "value_date", "amount", "amount_paise",
                "txn_amount", "value", "direction", "type", "txn_type", "dr_cr",
                "narration", "description", "remarks", "note", "counterparty",
                "counterparty_name", "payer", "payee", "vpa", "merchant_name",
                "reference", "ref_no", "utr", "invoice_id", "order_id", "batch_id",
                "mode", "payment_mode", "channel", "status", "state", "category", "tag"
            }}}

            records.append(
                RawTransactionRecord(
                    source_type=source_type,
                    source_id=source_id,
                    source_record_id=str(rec_id),
                    raw_date=raw_date,
                    raw_amount=raw_amount,
                    raw_direction=str(raw_dir) if raw_dir is not None else None,
                    raw_mode=str(raw_mode) if raw_mode is not None else None,
                    raw_narration=str(raw_narration) if raw_narration is not None else None,
                    raw_counterparty=str(raw_counterparty) if raw_counterparty is not None else None,
                    raw_reference=str(raw_reference) if raw_reference is not None else None,
                    raw_status=str(raw_status) if raw_status is not None else None,
                    raw_category=str(raw_category) if raw_category is not None else None,
                    metadata=item_meta,
                    raw_index=idx
                )
            )

        return records
