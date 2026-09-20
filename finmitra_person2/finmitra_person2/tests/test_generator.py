import numpy as np

from generate_dataset import generate_timeline, target_from_future


def test_generator_is_deterministic():
    first = generate_timeline("B1", "stable_retailer", np.random.default_rng(42))
    second = generate_timeline("B1", "stable_retailer", np.random.default_rng(42))
    assert first == second


def test_generator_produces_transaction_records_and_bounded_target():
    record = generate_timeline("B2", "growing_business", np.random.default_rng(7))
    assert len(record["transactions"]) > 100
    assert all("amount_paise" in item for item in record["transactions"])
    assert 0 <= target_from_future(record) <= 100


def test_target_uses_future_window():
    record = generate_timeline("B3", "stable_retailer", np.random.default_rng(9))
    baseline = target_from_future(record)
    cutoff = record["as_of_date"]
    changed = {**record, "transactions": [dict(item) for item in record["transactions"]]}
    for item in changed["transactions"]:
        if item["date"] > cutoff and item["direction"] == "CREDIT" and item["category"] == "BUSINESS_INCOME":
            item["amount_paise"] = max(1, item["amount_paise"] // 20)
    assert target_from_future(changed) != baseline
