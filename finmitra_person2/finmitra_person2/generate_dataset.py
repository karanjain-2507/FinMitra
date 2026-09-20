"""Generate synthetic transaction timelines and the five CLI fixtures."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import DATASET_PATH, OBSERVATION_MONTHS, RANDOM_SEED, ROOT, TARGET_MONTHS
from features.aggregation import monthly_frame, transaction_frame
from features.trends import normalized_trend
from schemas import NormalizedTransaction

ARCHETYPES: dict[str, dict[str, float]] = {
    "stable_retailer": {"weight": .17, "base": 70000, "growth": .002, "vol": .08, "season": .04, "expense": .70, "eligible": .98},
    "seasonal_farmer": {"weight": .13, "base": 42000, "growth": .002, "vol": .09, "season": .75, "expense": .62, "eligible": .94},
    "growing_business": {"weight": .13, "base": 48000, "growth": .022, "vol": .13, "season": .10, "expense": .66, "eligible": .97},
    "declining_business": {"weight": .13, "base": 80000, "growth": -.022, "vol": .16, "season": .08, "expense": .78, "eligible": .95},
    "volatile_business": {"weight": .12, "base": 62000, "growth": .000, "vol": .43, "season": .08, "expense": .72, "eligible": .95},
    "thin_file": {"weight": .08, "base": 38000, "growth": .004, "vol": .22, "season": .05, "expense": .73, "eligible": .90},
    "cash_heavy": {"weight": .08, "base": 52000, "growth": .003, "vol": .18, "season": .10, "expense": .70, "eligible": .58},
    "multi_source": {"weight": .08, "base": 85000, "growth": .007, "vol": .15, "season": .12, "expense": .69, "eligible": .98},
    "distressed_business": {"weight": .08, "base": 68000, "growth": -.032, "vol": .30, "season": .08, "expense": .91, "eligible": .92},
}


def _split(total: int, count: int, rng: np.random.Generator) -> list[int]:
    weights = rng.dirichlet(np.full(count, 2.0))
    values = np.maximum(1, np.floor(weights * total).astype(int))
    values[0] += total - int(values.sum())
    return [int(max(1, value)) for value in values]


def _season(month: pd.Period, amplitude: float, phase: float) -> float:
    return max(.12, 1 + amplitude * np.sin(2 * np.pi * (month.month - 1) / 12 + phase))


def _transaction(
    borrower_id: str,
    number: int,
    month: pd.Period,
    amount: int,
    direction: str,
    category: str,
    rng: np.random.Generator,
    *,
    eligible: bool = True,
    source: str = "ACCOUNT_AGGREGATOR",
    verification: str = "SOURCE_CONNECTED",
    counterparty: str | None = None,
) -> dict[str, Any]:
    return {
        "transaction_id": f"{borrower_id}-T{number:05d}",
        "date": (month.start_time + pd.Timedelta(days=int(rng.integers(0, 28)))).date().isoformat(),
        "amount_paise": int(amount),
        "direction": direction,
        "category": category,
        "category_confidence": .96 if eligible else .45,
        "mode": str(rng.choice(["UPI", "BANK_TRANSFER", "CARD", "CASH"])),
        "source": source,
        "verification": verification,
        "category_source": "SYNTHETIC_GROUND_TRUTH",
        "counterparty": counterparty,
        "status": "SUCCESS",
        "model_eligible": bool(eligible),
        "anomaly_flag": bool(rng.random() < .01),
        "provenance": {"synthetic": True},
    }


def generate_timeline(
    borrower_id: str,
    archetype: str,
    rng: np.random.Generator,
    cutoff: pd.Period = pd.Period("2026-08", freq="M"),
    include_future: bool = True,
) -> dict[str, Any]:
    cfg = ARCHETYPES[archetype]
    history_count = 2 if archetype == "thin_file" else OBSERVATION_MONTHS
    history = list(pd.period_range(end=cutoff, periods=history_count, freq="M"))
    future = list(pd.period_range(start=cutoff + 1, periods=TARGET_MONTHS, freq="M")) if include_future else []
    months = history + future
    base = float(cfg["base"] * rng.uniform(.75, 1.30)) * 100
    phase = float(rng.uniform(0, 2 * np.pi))
    customer_count = int(rng.integers(3, 14))
    customers = [f"{borrower_id}-C{i:02d}" for i in range(customer_count)]
    customer_weights = rng.dirichlet(np.linspace(2.0, .8, customer_count))
    rows: list[dict[str, Any]] = []
    number = 0
    for index, month in enumerate(months):
        relative_index = index - max(0, history_count - OBSERVATION_MONTHS)
        expected = base * max(.30, (1 + cfg["growth"]) ** relative_index) * _season(month, cfg["season"], phase)
        inflow = int(max(1000, expected * rng.lognormal(-cfg["vol"] ** 2 / 2, cfg["vol"])))
        if archetype in {"declining_business", "distressed_business"} and month in future:
            inflow = int(inflow * rng.uniform(.65, .88))
        persistent_cost = base * max(.35, (1 + max(cfg["growth"], -.008)) ** relative_index)
        outflow = int(max(1000, persistent_cost * cfg["expense"] * (.55 + .45 * _season(month, cfg["season"], phase)) * rng.lognormal(-.01, .12)))
        if archetype == "distressed_business" and month in future:
            outflow = int(outflow * rng.uniform(1.08, 1.28))
        inflow_count = int(rng.integers(5, 14))
        for amount in _split(inflow, inflow_count, rng):
            number += 1
            is_cash_heavy = archetype == "cash_heavy" and rng.random() > cfg["eligible"]
            category = "SELF_DECLARED_CASH_INCOME" if is_cash_heavy else str(rng.choice(["BUSINESS_INCOME", "POS_SETTLEMENT", "MARKETPLACE_SETTLEMENT"], p=[.74, .16, .10]))
            source = "CASH_DECLARATION" if is_cash_heavy else ("MULTI_SOURCE" if archetype == "multi_source" else "ACCOUNT_AGGREGATOR")
            rows.append(_transaction(
                borrower_id, number, month, amount, "CREDIT", category, rng,
                eligible=not is_cash_heavy,
                source=source,
                verification="SELF_DECLARED" if is_cash_heavy else "SOURCE_CONNECTED",
                counterparty=str(rng.choice(customers, p=customer_weights)),
            ))
        outflow_count = int(rng.integers(4, 10))
        for amount in _split(outflow, outflow_count, rng):
            number += 1
            rows.append(_transaction(
                borrower_id, number, month, amount, "DEBIT",
                str(rng.choice(["INVENTORY", "SUPPLIER_PURCHASE", "BUSINESS_UTILITY"], p=[.62, .28, .10])),
                rng, counterparty=f"{borrower_id}-SUP{int(rng.integers(1, 6))}",
            ))
        if rng.random() < .25:
            number += 1
            rows.append(_transaction(borrower_id, number, month, int(rng.uniform(500, 5000) * 100), "CREDIT", "SELF_TRANSFER", rng, counterparty=f"{borrower_id}-OWN"))
        if rng.random() < .08:
            number += 1
            rows.append(_transaction(borrower_id, number, month, int(rng.uniform(5000, 20000) * 100), "CREDIT", "LOAN_DISBURSEMENT", rng, counterparty="LENDER"))
    return {
        "borrower_id": borrower_id,
        "archetype": archetype,
        "as_of_date": cutoff.end_time.date().isoformat(),
        "history_start": history[0].start_time.date().isoformat(),
        "transactions": rows,
    }


def target_from_future(record: dict[str, Any]) -> float:
    cutoff = record["as_of_date"]
    transactions = tuple(NormalizedTransaction.from_dict(item) for item in record["transactions"])
    future_rows = [item for item in transactions if item.date > cutoff]
    if not future_rows:
        raise ValueError("target requires future transactions")
    last_date = max(item.date for item in future_rows)
    frame, _ = transaction_frame(tuple(future_rows), last_date)
    monthly = monthly_frame(frame, last_date).iloc[-TARGET_MONTHS:]
    inflow, net = monthly["inflow"], monthly["net"]
    mean_inflow = max(float(inflow.mean()), 1.0)
    margin = float(net.mean()) / mean_inflow
    surplus_score = float(np.clip(50 + 100 * margin, 0, 100))
    stability_score = float(100 / (1 + (inflow.std(ddof=0) / mean_inflow)))
    positive_score = float((net > 0).mean() * 100)
    trend_score = float(50 + 50 * np.tanh(5 * normalized_trend(net)))
    return round(float(np.clip(.35 * surplus_score + .25 * stability_score + .20 * positive_score + .20 * trend_score, 0, 100)), 4)


def write_fixtures(seed: int = RANDOM_SEED) -> None:
    mapping = {
        "stable_kirana": "stable_retailer",
        "seasonal_farmer": "seasonal_farmer",
        "growing_business": "growing_business",
        "declining_business": "declining_business",
        "thin_file": "thin_file",
    }
    for offset, (fixture, archetype) in enumerate(mapping.items()):
        rng = np.random.default_rng(seed + 10_000 + offset)
        record = generate_timeline(f"FIX-{fixture.upper()}", archetype, rng, include_future=False)
        record.pop("archetype")
        record.pop("history_start")
        path = ROOT / "fixtures" / fixture / "input.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def generate_dataset(n_borrowers: int = 600, seed: int = RANDOM_SEED, output: Path = DATASET_PATH) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    names = list(ARCHETYPES)
    weights = np.array([ARCHETYPES[name]["weight"] for name in names], dtype=float)
    weights /= weights.sum()
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = {"train": 0, "validation": 0, "test": 0}
    archetype_counts = {name: 0 for name in names}
    with output.open("w", encoding="utf-8") as stream:
        for index in range(n_borrowers):
            archetype = str(rng.choice(names, p=weights))
            split_index = index % 20
            split = "train" if split_index < 14 else "validation" if split_index < 17 else "test"
            record = generate_timeline(f"SYN-{index + 1:06d}", archetype, rng)
            record["split"] = split
            record["target_cashflow_health"] = target_from_future(record)
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")
            counts[split] += 1
            archetype_counts[archetype] += 1
    write_fixtures(seed)
    metadata = {
        "synthetic": True,
        "seed": seed,
        "borrowers": n_borrowers,
        "split_counts": counts,
        "archetype_counts": archetype_counts,
        "target": "35% future surplus margin + 25% future inflow stability + 20% positive-net month rate + 20% future net trend",
        "warning": "Synthetic hackathon data; no real-world predictive validity is established.",
    }
    (output.parent / "dataset_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--borrowers", type=int, default=600)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--output", type=Path, default=DATASET_PATH)
    args = parser.parse_args()
    metadata = generate_dataset(args.borrowers, args.seed, args.output)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
