"""Public Person 1 -> Person 2 and Person 2 -> Person 4 contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Mapping

from enums import AssessmentStatus, Direction, ReasonDirection, TransactionStatus


class SchemaError(ValueError):
    pass


def _date(value: Any) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise SchemaError("date must be YYYY-MM-DD") from exc


@dataclass(frozen=True)
class NormalizedTransaction:
    transaction_id: str
    date: str
    amount_paise: int
    direction: str
    category: str
    category_confidence: float
    mode: str
    source: str
    verification: str
    category_source: str
    counterparty: str | None
    status: str
    model_eligible: bool
    balance_after_paise: int | None = None
    anomaly_flag: bool = False
    provenance: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "NormalizedTransaction":
        required = {
            "transaction_id", "date", "amount_paise", "direction", "category",
            "category_confidence", "mode", "source", "verification",
            "category_source", "status", "model_eligible",
        }
        missing = sorted(required - set(raw))
        if missing:
            raise SchemaError(f"transaction missing fields: {missing}")
        amount = raw["amount_paise"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise SchemaError("amount_paise must be a positive integer")
        confidence = float(raw["category_confidence"])
        if not 0 <= confidence <= 1:
            raise SchemaError("category_confidence must be between 0 and 1")
        direction = str(raw["direction"])
        status = str(raw["status"])
        if direction not in {item.value for item in Direction}:
            raise SchemaError(f"invalid direction: {direction}")
        if status not in {item.value for item in TransactionStatus}:
            raise SchemaError(f"invalid status: {status}")
        transaction_id = str(raw["transaction_id"]).strip()
        if not transaction_id:
            raise SchemaError("transaction_id cannot be empty")
        return cls(
            transaction_id=transaction_id,
            date=_date(raw["date"]),
            amount_paise=amount,
            direction=direction,
            category=str(raw["category"]).upper(),
            category_confidence=confidence,
            mode=str(raw["mode"]),
            source=str(raw["source"]),
            verification=str(raw["verification"]),
            category_source=str(raw["category_source"]),
            counterparty=None if raw.get("counterparty") is None else str(raw["counterparty"]),
            status=status,
            model_eligible=bool(raw["model_eligible"]),
            balance_after_paise=(
                None
                if raw.get("balance_after_paise") is None
                else int(raw["balance_after_paise"])
            ),
            anomaly_flag=bool(raw.get("anomaly_flag", False)),
            provenance=dict(raw.get("provenance", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BorrowerInput:
    borrower_id: str
    as_of_date: str
    transactions: tuple[NormalizedTransaction, ...]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "BorrowerInput":
        borrower_id = str(raw.get("borrower_id", "")).strip()
        if not borrower_id:
            raise SchemaError("borrower_id cannot be empty")
        transactions = tuple(
            NormalizedTransaction.from_dict(item) for item in raw.get("transactions", [])
        )
        return cls(borrower_id, _date(raw["as_of_date"]), transactions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "borrower_id": self.borrower_id,
            "as_of_date": self.as_of_date,
            "transactions": [item.to_dict() for item in self.transactions],
        }


@dataclass(frozen=True)
class Reason:
    code: str
    direction: str
    impact: float
    message: str

    def __post_init__(self) -> None:
        if not self.code.startswith("CF") or len(self.code) != 4 or not self.code[2:].isdigit():
            raise SchemaError(f"invalid cash-flow reason code: {self.code}")
        if self.direction not in {item.value for item in ReasonDirection}:
            raise SchemaError(f"invalid reason direction: {self.direction}")


@dataclass(frozen=True)
class CashflowResult:
    component: str
    version: str
    score: float | None
    status: str
    confidence: float
    features: Mapping[str, Any]
    stress_probability: float | None = None
    reasons: tuple[Reason, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.component != "cashflow":
            raise SchemaError("component must be cashflow")
        if self.score is not None and not 0 <= self.score <= 100:
            raise SchemaError("score must be null or between 0 and 100")
        if self.stress_probability is not None and not 0 <= self.stress_probability <= 1:
            raise SchemaError("stress_probability must be null or between 0 and 1")
        if not 0 <= self.confidence <= 1:
            raise SchemaError("confidence must be between 0 and 1")
        if self.status not in {item.value for item in AssessmentStatus}:
            raise SchemaError(f"invalid assessment status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
