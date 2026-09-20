import pytest

from schemas import CashflowResult, NormalizedTransaction, SchemaError


def valid_transaction() -> dict:
    return {
        "transaction_id": "T1", "date": "2026-01-01", "amount_paise": 10000,
        "direction": "CREDIT", "category": "BUSINESS_INCOME", "category_confidence": .9,
        "mode": "UPI", "source": "AA", "verification": "SOURCE_CONNECTED",
        "category_source": "RULE", "counterparty": "C1", "status": "SUCCESS",
        "model_eligible": True,
    }


def test_valid_transaction_parses():
    assert NormalizedTransaction.from_dict(valid_transaction()).amount_paise == 10000


@pytest.mark.parametrize("field", ["transaction_id", "date", "amount_paise", "direction", "category"])
def test_required_transaction_fields(field):
    raw = valid_transaction()
    raw.pop(field)
    with pytest.raises(SchemaError):
        NormalizedTransaction.from_dict(raw)


def test_invalid_money_and_confidence_rejected():
    raw = valid_transaction()
    raw["amount_paise"] = 1.5
    with pytest.raises(SchemaError):
        NormalizedTransaction.from_dict(raw)
    raw = valid_transaction()
    raw["category_confidence"] = 1.2
    with pytest.raises(SchemaError):
        NormalizedTransaction.from_dict(raw)


def test_result_ranges_are_enforced():
    with pytest.raises(SchemaError):
        CashflowResult("cashflow", "1", 101, "SUFFICIENT", .8, {})
    with pytest.raises(SchemaError):
        CashflowResult("cashflow", "1", 50, "SUFFICIENT", 1.1, {})
