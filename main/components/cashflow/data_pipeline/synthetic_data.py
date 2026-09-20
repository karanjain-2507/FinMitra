# synthetic_data_generator.py

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


HISTORY_MONTHS = 24
FUTURE_MONTHS = 3
SEED = 42

ARCHETYPES = {
    "kirana": {
        "weight": 0.28,
        "monthly_income": (45_000, 120_000),
        "expense_ratio": (0.70, 0.88),
        "volatility": 0.16,
        "seasonality": 0.08,
        "transactions": (18, 34),
        "customers": (18, 45),
    },
    "dairy": {
        "weight": 0.20,
        "monthly_income": (22_000, 55_000),
        "expense_ratio": (0.62, 0.80),
        "volatility": 0.11,
        "seasonality": 0.10,
        "transactions": (10, 20),
        "customers": (3, 8),
    },
    "gig_worker": {
        "weight": 0.20,
        "monthly_income": (25_000, 60_000),
        "expense_ratio": (0.55, 0.76),
        "volatility": 0.20,
        "seasonality": 0.08,
        "transactions": (12, 24),
        "customers": (2, 5),
    },
    "artisan": {
        "weight": 0.17,
        "monthly_income": (15_000, 50_000),
        "expense_ratio": (0.58, 0.80),
        "volatility": 0.32,
        "seasonality": 0.24,
        "transactions": (4, 10),
        "customers": (5, 15),
    },
    "seasonal_farmer": {
        "weight": 0.15,
        "monthly_income": (18_000, 65_000),
        "expense_ratio": (0.50, 0.75),
        "volatility": 0.14,
        "seasonality": 0.72,
        "transactions": (2, 6),
        "customers": (2, 6),
    },
}


def split_amount(total: int, count: int, rng: np.random.Generator) -> list[int]:
    weights = rng.dirichlet(np.full(count, 2.0))
    amounts = np.floor(weights * total).astype(int)
    amounts[0] += total - amounts.sum()
    return amounts.tolist()


def seasonal_multiplier(month: int, amplitude: float, phase: float) -> float:
    angle = 2 * np.pi * (month - 1) / 12 + phase
    return max(0.15, 1 + amplitude * np.sin(angle))


def choose_source(rng: np.random.Generator) -> dict:
    channel = rng.choice(
        ["UPI", "BANK", "POS", "CASH"],
        p=[0.48, 0.20, 0.17, 0.15],
    )

    sources = {
        "UPI": {
            "mode": "UPI",
            "source_type": "UPI_EXPORT",
            "verification": "SOURCE_CONNECTED",
            "confidence": 0.96,
            "category_source": "MERCHANT_QR_MATCH",
        },
        "BANK": {
            "mode": "BANK_TRANSFER",
            "source_type": "ACCOUNT_AGGREGATOR",
            "verification": "SOURCE_CONNECTED",
            "confidence": 0.94,
            "category_source": "COUNTERPARTY_AND_NARRATION",
        },
        "POS": {
            "mode": "CARD",
            "source_type": "BANK_STATEMENT",
            "verification": "SOURCE_CONNECTED",
            "confidence": 0.98,
            "category_source": "POS_SETTLEMENT",
        },
        "CASH": {
            "mode": "CASH",
            "source_type": "RECEIPT",
            "verification": "DOCUMENT_UPLOADED",
            "confidence": 0.78,
            "category_source": "RECEIPT_LEDGER_MATCH",
        },
    }

    return sources[channel]


def calculate_label(
    borrower_transactions: pd.DataFrame,
    historical_months: list[pd.Period],
    future_months: list[pd.Period],
) -> dict:
    successful = borrower_transactions[
        borrower_transactions["status"] == "SUCCESS"
    ].copy()

    business_income = successful[
        (successful["direction"] == "CREDIT")
        & (successful["category"] == "BUSINESS_INCOME")
    ]

    business_expenses = successful[
        (successful["direction"] == "DEBIT")
        & successful["category"].isin(
            ["INVENTORY", "BUSINESS_ESSENTIAL", "UTILITY"]
        )
    ]

    monthly_income = business_income.groupby("month")["amount_paise"].sum()
    monthly_expenses = business_expenses.groupby("month")["amount_paise"].sum()

    historical_values = [
        int(monthly_income.get(str(month), 0))
        for month in historical_months
    ]

    historical_median = int(np.median(historical_values))

    drop_flags = []
    future_incomes = []
    future_surpluses = []
    expected_incomes = []

    for future_month in future_months:
        matching_historical_months = [
            month
            for month in historical_months
            if month.month == future_month.month
        ]

        previous_values = [
            int(monthly_income.get(str(month), 0))
            for month in matching_historical_months
        ]

        expected_income = (
            int(np.median(previous_values))
            if previous_values
            else historical_median
        )

        actual_income = int(monthly_income.get(str(future_month), 0))
        actual_expenses = int(monthly_expenses.get(str(future_month), 0))
        operating_surplus = actual_income - actual_expenses

        expected_incomes.append(expected_income)
        future_incomes.append(actual_income)
        future_surpluses.append(operating_surplus)

        drop_flags.append(
            expected_income > 0
            and actual_income <= expected_income * 0.65
        )

    consecutive_income_drop = any(
        drop_flags[i] and drop_flags[i + 1]
        for i in range(len(drop_flags) - 1)
    )

    negative_cashflow = any(
        surplus < 0 for surplus in future_surpluses
    )

    return {
        "cashflow_stress_90d": bool(
            consecutive_income_drop or negative_cashflow
        ),
        "two_consecutive_35pct_income_drops": bool(
            consecutive_income_drop
        ),
        "negative_operating_cashflow_30d": bool(negative_cashflow),
        "historical_median_monthly_income_paise": historical_median,
        "future_month_1_expected_income_paise": expected_incomes[0],
        "future_month_2_expected_income_paise": expected_incomes[1],
        "future_month_3_expected_income_paise": expected_incomes[2],
        "future_month_1_income_paise": future_incomes[0],
        "future_month_2_income_paise": future_incomes[1],
        "future_month_3_income_paise": future_incomes[2],
        "future_month_1_surplus_paise": future_surpluses[0],
        "future_month_2_surplus_paise": future_surpluses[1],
        "future_month_3_surplus_paise": future_surpluses[2],
    }


def generate_borrower(
    borrower_number: int,
    as_of_month: pd.Period,
    rng: np.random.Generator,
) -> tuple[list[dict], dict, dict]:
    borrower_id = f"CF-{borrower_number:06d}"

    archetype_names = list(ARCHETYPES)
    weights = np.array(
        [ARCHETYPES[name]["weight"] for name in archetype_names]
    )
    weights = weights / weights.sum()

    archetype = rng.choice(archetype_names, p=weights)
    config = ARCHETYPES[archetype]

    base_income_rupees = rng.uniform(*config["monthly_income"])
    base_income_paise = int(base_income_rupees * 100)

    # Persistent borrower condition. It is never exposed to the model, but it
    # affects both the observed history and the probability of future stress.
    # This fixes the old generator where future shocks were independent of all
    # historical evidence and therefore impossible to predict.
    latent_risk = float(rng.beta(2.2, 3.0))

    expense_ratio = float(
        np.clip(
            rng.uniform(*config["expense_ratio"])
            + 0.10 * (latent_risk - 0.40),
            0.45,
            0.94,
        )
    )
    monthly_trend = float(
        np.clip(
            rng.normal(0.008 - 0.028 * latent_risk, 0.004),
            -0.025,
            0.015,
        )
    )
    effective_volatility = float(
        config["volatility"] * (0.72 + 0.90 * latent_risk)
    )
    seasonal_phase = rng.uniform(0, 2 * np.pi)

    customer_count = rng.integers(
        config["customers"][0],
        config["customers"][1] + 1,
    )

    customers = [
        f"{borrower_id}-CUSTOMER-{i:03d}"
        for i in range(1, customer_count + 1)
    ]

    customer_concentration = np.maximum(
        0.20,
        np.linspace(2.2, 0.8, customer_count) * (1.45 - latent_risk),
    )
    customer_weights = rng.dirichlet(customer_concentration)

    historical_months = list(
        pd.period_range(
            end=as_of_month,
            periods=HISTORY_MONTHS,
            freq="M",
        )
    )

    future_months = list(
        pd.period_range(
            start=as_of_month + 1,
            periods=FUTURE_MONTHS,
            freq="M",
        )
    )

    all_months = historical_months + future_months

    future_shock_probability = float(
        np.clip(0.05 + 0.70 * latent_risk, 0.05, 0.78)
    )
    scenario = rng.choice(
        ["NONE", "INFLOW_DROP", "EXPENSE_SPIKE", "BOTH"],
        p=[
            1 - future_shock_probability,
            future_shock_probability * 0.48,
            future_shock_probability * 0.37,
            future_shock_probability * 0.15,
        ],
    )

    # Some vulnerable businesses begin deteriorating during the final six
    # observed months. The deterioration continues into the future, creating
    # a learnable warning signal without placing future data in the features.
    deterioration_strength = float(
        max(0.0, latent_risk - rng.uniform(0.30, 0.78)) * 0.85
    )

    drop_start = int(rng.integers(0, 2))
    expense_spike_month = int(rng.integers(0, 3))

    transactions = []
    transaction_number = 0

    for month_index, month in enumerate(all_months):
        period = (
            "HISTORY"
            if month in historical_months
            else "FUTURE"
        )

        seasonality = seasonal_multiplier(
            month.month,
            config["seasonality"],
            seasonal_phase,
        )

        trend = max(0.65, 1 + monthly_trend * month_index)

        income_noise = rng.lognormal(
            mean=-(effective_volatility ** 2) / 2,
            sigma=effective_volatility,
        )

        monthly_income = int(
            max(
                10_000,
                base_income_paise
                * seasonality
                * trend
                * income_noise,
            )
        )

        deterioration_progress = float(
            np.clip((month_index - (HISTORY_MONTHS - 7)) / 6, 0, 1)
        )
        monthly_income = int(
            monthly_income
            * (1 - deterioration_strength * deterioration_progress)
        )

        future_index = (
            future_months.index(month)
            if month in future_months
            else None
        )

        if (
            future_index is not None
            and scenario in {"INFLOW_DROP", "BOTH"}
            and drop_start <= future_index <= drop_start + 1
        ):
            monthly_income = int(
                monthly_income * rng.uniform(0.30, 0.48)
            )

        expense_noise = rng.lognormal(
            mean=-0.5 * 0.12**2,
            sigma=0.12,
        )

        monthly_expenses = int(
            max(
                8_000,
                monthly_income * expense_ratio * expense_noise,
            )
        )
        monthly_expenses = int(
            monthly_expenses
            * (1 + 0.35 * deterioration_strength * deterioration_progress)
        )

        if (
            future_index is not None
            and scenario in {"EXPENSE_SPIKE", "BOTH"}
            and future_index == expense_spike_month
        ):
            monthly_expenses = max(
                monthly_expenses,
                int(monthly_income * rng.uniform(1.15, 1.45)),
            )

        income_transaction_count = int(
            rng.integers(
                config["transactions"][0],
                config["transactions"][1] + 1,
            )
        )

        for amount in split_amount(
            monthly_income,
            income_transaction_count,
            rng,
        ):
            transaction_number += 1
            source = choose_source(rng)

            transactions.append(
                {
                    "borrower_id": borrower_id,
                    "transaction_id": (
                        f"{borrower_id}-T{transaction_number:05d}"
                    ),
                    "date": (
                        month.start_time
                        + pd.Timedelta(days=int(rng.integers(0, 28)))
                    ).date().isoformat(),
                    "month": str(month),
                    "amount_paise": amount,
                    "direction": "CREDIT",
                    "category": "BUSINESS_INCOME",
                    "category_confidence": source["confidence"],
                    "category_source": source["category_source"],
                    "counterparty_id": rng.choice(
                        customers,
                        p=customer_weights,
                    ),
                    "mode": source["mode"],
                    "source_type": source["source_type"],
                    "verification": source["verification"],
                    "status": "SUCCESS",
                    "period": period,
                }
            )

        expense_count = int(rng.integers(5, 12))
        expense_amounts = split_amount(
            monthly_expenses,
            expense_count,
            rng,
        )

        expense_categories = rng.choice(
            ["INVENTORY", "BUSINESS_ESSENTIAL", "UTILITY"],
            size=expense_count,
            p=[0.68, 0.22, 0.10],
        )

        for amount, category in zip(
            expense_amounts,
            expense_categories,
        ):
            transaction_number += 1

            transactions.append(
                {
                    "borrower_id": borrower_id,
                    "transaction_id": (
                        f"{borrower_id}-T{transaction_number:05d}"
                    ),
                    "date": (
                        month.start_time
                        + pd.Timedelta(days=int(rng.integers(0, 28)))
                    ).date().isoformat(),
                    "month": str(month),
                    "amount_paise": amount,
                    "direction": "DEBIT",
                    "category": category,
                    "category_confidence": 0.92,
                    "category_source": "NARRATION_RULE",
                    "counterparty_id": (
                        f"{borrower_id}-SUPPLIER-"
                        f"{rng.integers(1, 7):02d}"
                    ),
                    "mode": rng.choice(
                        ["UPI", "BANK_TRANSFER", "CASH"],
                        p=[0.42, 0.42, 0.16],
                    ),
                    "source_type": "ACCOUNT_AGGREGATOR",
                    "verification": "SOURCE_CONNECTED",
                    "status": "SUCCESS",
                    "period": period,
                }
            )

        if rng.random() < 0.22:
            transaction_number += 1

            transactions.append(
                {
                    "borrower_id": borrower_id,
                    "transaction_id": (
                        f"{borrower_id}-T{transaction_number:05d}"
                    ),
                    "date": (
                        month.start_time
                        + pd.Timedelta(days=int(rng.integers(0, 28)))
                    ).date().isoformat(),
                    "month": str(month),
                    "amount_paise": int(
                        rng.uniform(500, 6_000) * 100
                    ),
                    "direction": "CREDIT",
                    "category": "SELF_TRANSFER",
                    "category_confidence": 0.99,
                    "category_source": "OWN_ACCOUNT_MATCH",
                    "counterparty_id": (
                        f"{borrower_id}-OWN-ACCOUNT"
                    ),
                    "mode": "BANK_TRANSFER",
                    "source_type": "ACCOUNT_AGGREGATOR",
                    "verification": "SOURCE_CONNECTED",
                    "status": "SUCCESS",
                    "period": period,
                }
            )

    borrower_transactions = pd.DataFrame(transactions)

    label = calculate_label(
        borrower_transactions,
        historical_months,
        future_months,
    )

    split_value = borrower_number % 20

    if split_value < 14:
        split = "train"
    elif split_value < 17:
        split = "validation"
    else:
        split = "test"

    borrower = {
        "borrower_id": borrower_id,
        "split": split,
        "simulator_only_archetype": archetype,
        "simulator_only_latent_risk": latent_risk,
        "history_start": str(historical_months[0]),
        "history_end": str(historical_months[-1]),
        "future_end": str(future_months[-1]),
    }

    label_row = {
        "borrower_id": borrower_id,
        "split": split,
        **label,
        "simulator_only_scenario": scenario,
        "simulator_only_latent_risk": latent_risk,
    }

    return transactions, borrower, label_row


def generate_dataset(
    number_of_borrowers: int,
    seed: int,
    as_of_month: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    cutoff = pd.Period(as_of_month, freq="M")

    all_transactions = []
    borrowers = []
    labels = []

    for borrower_number in range(1, number_of_borrowers + 1):
        transactions, borrower, label = generate_borrower(
            borrower_number,
            cutoff,
            rng,
        )

        all_transactions.extend(transactions)
        borrowers.append(borrower)
        labels.append(label)

    transactions_df = pd.DataFrame(all_transactions)
    borrowers_df = pd.DataFrame(borrowers)
    labels_df = pd.DataFrame(labels)

    metadata = {
        "dataset_name": "finmitra_cashflow_synthetic_v2_learnable",
        "synthetic": True,
        "seed": seed,
        "borrower_count": number_of_borrowers,
        "history_months": HISTORY_MONTHS,
        "future_months": FUTURE_MONTHS,
        "as_of_month": as_of_month,
        "stress_rate": float(
            labels_df["cashflow_stress_90d"].mean()
        ),
        "label_definition": {
            "condition_1": (
                "Business inflow falls at least 35% below its "
                "seasonally expected level for two consecutive months."
            ),
            "condition_2": (
                "Operating cash flow is negative for at least "
                "one future 30-day month."
            ),
        },
        "warning": (
            "Synthetic hackathon data only. This is not empirical "
            "borrower data or a bank-ready risk model."
        ),
        "never_use_as_model_features": [
            "simulator_only_archetype",
            "simulator_only_scenario",
            "simulator_only_latent_risk",
        ],
    }

    return (
        transactions_df,
        borrowers_df,
        labels_df,
        metadata,
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--borrowers",
        type=int,
        default=500,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
    )

    parser.add_argument(
        "--as-of-month",
        default="2026-08",
    )

    parser.add_argument(
        "--output",
        default="cashflow_synthetic_data",
    )

    args = parser.parse_args()

    output_directory = Path(args.output)
    output_directory.mkdir(parents=True, exist_ok=True)

    transactions, borrowers, labels, metadata = generate_dataset(
        number_of_borrowers=args.borrowers,
        seed=args.seed,
        as_of_month=args.as_of_month,
    )

    transactions.to_csv(
        output_directory / "transactions.csv",
        index=False,
    )

    borrowers.to_csv(
        output_directory / "borrowers.csv",
        index=False,
    )

    labels.to_csv(
        output_directory / "labels.csv",
        index=False,
    )

    with open(
        output_directory / "metadata.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(metadata, file, indent=2)

    print(
        f"Generated {len(transactions):,} transactions "
        f"for {len(borrowers):,} borrowers."
    )

    print(
        f"Cash-flow stress rate: "
        f"{metadata['stress_rate']:.2%}"
    )

    print(f"Files saved to: {output_directory.resolve()}")


if __name__ == "__main__":
    main()
