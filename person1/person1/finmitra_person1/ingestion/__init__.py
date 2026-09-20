"""
Ingestion module for FinMitra Person 1.
Provides unified dispatching for heterogeneous financial sources.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import json

from ..enums import DataSourceType
from ..schemas import BorrowerInput, SourceInput
from .base import RawTransactionRecord, SourceAdapter
from .json_adapter import JsonSourceAdapter
from .csv_adapter import CsvSourceAdapter
from .bank_statement import BankStatementAdapter
from .upi import UpiAdapter
from .pos import PosAdapter
from .marketplace import MarketplaceAdapter
from .ledger import BusinessLedgerAdapter
from .invoices import InvoiceAdapter
from .cash_records import CashRecordsAdapter


ADAPTER_REGISTRY: Dict[DataSourceType, SourceAdapter] = {
    DataSourceType.BANK_STATEMENT: BankStatementAdapter(),
    DataSourceType.UPI: UpiAdapter(),
    DataSourceType.QR: UpiAdapter(),
    DataSourceType.POS: PosAdapter(),
    DataSourceType.MARKETPLACE: MarketplaceAdapter(),
    DataSourceType.BUSINESS_LEDGER: BusinessLedgerAdapter(),
    DataSourceType.INVOICE: InvoiceAdapter(),
    DataSourceType.SUPPLIER_RECORD: InvoiceAdapter(),
    DataSourceType.RECEIPT: CashRecordsAdapter(),
    DataSourceType.CASH_RECORD: CashRecordsAdapter(),
    DataSourceType.SELF_DECLARATION: CashRecordsAdapter(),
    DataSourceType.OTHER: JsonSourceAdapter(),
}


def get_adapter(source_type: DataSourceType) -> SourceAdapter:
    """Retrieve the registered adapter for a given source type."""
    return ADAPTER_REGISTRY.get(source_type, JsonSourceAdapter())


def ingest_source(source_input: SourceInput) -> List[RawTransactionRecord]:
    """Ingest a single SourceInput into raw records."""
    adapter = get_adapter(source_input.source_type)
    return adapter.parse(
        payload=source_input.records,
        source_id=source_input.source_id,
        source_type=source_input.source_type,
        metadata=source_input.metadata
    )


def ingest_borrower(borrower: BorrowerInput) -> List[RawTransactionRecord]:
    """Ingest all sources in a BorrowerInput payload."""
    all_records: List[RawTransactionRecord] = []
    for src in borrower.sources:
        records = ingest_source(src)
        all_records.extend(records)
    return all_records


def parse_borrower_payload(data: Any) -> BorrowerInput:
    """
    Parse a Python dictionary, JSON string, or BorrowerInput object
    into a validated BorrowerInput.
    """
    if isinstance(data, BorrowerInput):
        return data
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, dict):
        return BorrowerInput.model_validate(data)
    raise ValueError(f"Cannot parse borrower payload from type {type(data)}")
