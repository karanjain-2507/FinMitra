"""
Generic CSV source adapter.
Parses CSV strings or files into RawTransactionRecord objects.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import csv
import io

from ..enums import DataSourceType
from .base import RawTransactionRecord


class CsvSourceAdapter:
    """Parses CSV tabular data into list of RawTransactionRecords."""

    def parse(
        self,
        payload: Any,
        source_id: str,
        source_type: DataSourceType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[RawTransactionRecord]:
        records: List[RawTransactionRecord] = []
        meta = metadata or {}

        csv_text: str = ""
        if isinstance(payload, str):
            csv_text = payload
        elif isinstance(payload, bytes):
            csv_text = payload.decode("utf-8", errors="replace")
        elif hasattr(payload, "read"):
            csv_text = payload.read()
            if isinstance(csv_text, bytes):
                csv_text = csv_text.decode("utf-8", errors="replace")
        else:
            return [
                RawTransactionRecord(
                    source_type=source_type,
                    source_id=source_id,
                    source_record_id=None,
                    raw_date=None,
                    raw_amount=None,
                    metadata={"raw_error": "Unsupported CSV payload type"}
                )
            ]

        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            for idx, row in enumerate(reader):
                # Normalize keys by stripping and lowercasing for lookup
                normalized_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}

                rec_id = (
                    normalized_row.get("transaction id")
                    or normalized_row.get("transaction_id")
                    or normalized_row.get("txnid")
                    or normalized_row.get("id")
                    or normalized_row.get("ref no")
                    or normalized_row.get("reference")
                    or f"CSV-{idx+1}"
                )
                raw_date = (
                    normalized_row.get("date")
                    or normalized_row.get("txn date")
                    or normalized_row.get("transaction date")
                    or normalized_row.get("value date")
                )

                # Check for separate Credit and Debit columns
                credit_val = normalized_row.get("credit") or normalized_row.get("deposit") or normalized_row.get("cr")
                debit_val = normalized_row.get("debit") or normalized_row.get("withdrawal") or normalized_row.get("dr")

                def _parse_num(val_str: Optional[str]) -> Optional[float]:
                    if not val_str:
                        return None
                    try:
                        c = val_str.replace(",", "").replace("₹", "").replace("$", "").strip()
                        return float(c)
                    except ValueError:
                        return None

                c_num = _parse_num(credit_val)
                d_num = _parse_num(debit_val)

                if c_num is not None and c_num > 0:
                    raw_amount = credit_val
                    raw_direction = "CREDIT"
                elif d_num is not None and d_num > 0:
                    raw_amount = debit_val
                    raw_direction = "DEBIT"
                else:
                    raw_amount = (
                        normalized_row.get("amount")
                        or normalized_row.get("txn amount")
                        or normalized_row.get("total")
                    )
                    raw_direction = (
                        normalized_row.get("direction")
                        or normalized_row.get("type")
                        or normalized_row.get("dr/cr")
                    )

                raw_narration = (
                    normalized_row.get("narration")
                    or normalized_row.get("description")
                    or normalized_row.get("particulars")
                    or normalized_row.get("remarks")
                )
                raw_counterparty = (
                    normalized_row.get("counterparty")
                    or normalized_row.get("party")
                    or normalized_row.get("merchant")
                    or normalized_row.get("payer/payee")
                )
                raw_reference = (
                    normalized_row.get("reference")
                    or normalized_row.get("utr")
                    or normalized_row.get("chq/ref no")
                    or normalized_row.get("invoice no")
                )
                raw_mode = normalized_row.get("mode") or normalized_row.get("channel")
                raw_status = normalized_row.get("status")

                records.append(
                    RawTransactionRecord(
                        source_type=source_type,
                        source_id=source_id,
                        source_record_id=str(rec_id),
                        raw_date=raw_date,
                        raw_amount=raw_amount,
                        raw_direction=raw_direction,
                        raw_mode=raw_mode,
                        raw_narration=raw_narration,
                        raw_counterparty=raw_counterparty,
                        raw_reference=raw_reference,
                        raw_status=raw_status,
                        metadata={**meta, "raw_row": row},
                        raw_index=idx
                    )
                )

        except Exception as e:
            records.append(
                RawTransactionRecord(
                    source_type=source_type,
                    source_id=source_id,
                    source_record_id=None,
                    raw_date=None,
                    raw_amount=None,
                    metadata={"raw_error": f"CSV parse error: {str(e)}"}
                )
            )

        return records
