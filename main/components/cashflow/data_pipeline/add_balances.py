# 1_add_balances.py

from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIRECTORY = Path("cashflow_synthetic_data_v2")
TRANSACTIONS_FILE = DATA_DIRECTORY / "transactions.csv"
SEED = 42


def add_household_expenses_and_balances(
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)

    transactions["date"] = pd.to_datetime(transactions["date"])
    transactions["amount_paise"] = transactions["amount_paise"].astype("int64")

    successful = transactions["status"].eq("SUCCESS")

    business_income = transactions[
        successful
        & transactions["direction"].eq("CREDIT")
        & transactions["category"].eq("BUSINESS_INCOME")
    ]

    business_expenses = transactions[
        successful
        & transactions["direction"].eq("DEBIT")
        & transactions["category"].isin(
            ["INVENTORY", "BUSINESS_ESSENTIAL", "UTILITY"]
        )
    ]

    monthly_income = business_income.groupby(
        ["borrower_id", "month"]
    )["amount_paise"].sum()

    monthly_expense = business_expenses.groupby(
        ["borrower_id", "month"]
    )["amount_paise"].sum()

    monthly_summary = (
        pd.concat(
            [
                monthly_income.rename("income"),
                monthly_expense.rename("expense"),
            ],
            axis=1,
        )
        .fillna(0)
        .reset_index()
    )

    period_by_borrower_month = (
        transactions.groupby(["borrower_id", "month"])["period"]
        .first()
        .to_dict()
    )

    household_rows = []

    for row in monthly_summary.itertuples(index=False):
        operating_surplus = max(0, int(row.income - row.expense))

        household_amount = int(
            operating_surplus * rng.uniform(0.55, 0.82)
        )

        if household_amount <= 0:
            continue

        period = period_by_borrower_month[(row.borrower_id, row.month)]
        month_period = pd.Period(row.month, freq="M")

        household_rows.append(
            {
                "borrower_id": row.borrower_id,
                "transaction_id": (
                    f"{row.borrower_id}-HOUSEHOLD-{row.month}"
                ),
                "date": (
                    month_period.start_time
                    + pd.Timedelta(days=24)
                ),
                "month": row.month,
                "amount_paise": household_amount,
                "direction": "DEBIT",
                "category": "HOUSEHOLD_ESSENTIAL",
                "category_confidence": 0.90,
                "category_source": "NARRATION_RULE",
                "counterparty_id": (
                    f"{row.borrower_id}-HOUSEHOLD"
                ),
                "mode": "UPI",
                "source_type": "ACCOUNT_AGGREGATOR",
                "verification": "SOURCE_CONNECTED",
                "status": "SUCCESS",
                "period": period,
            }
        )

    transactions = pd.concat(
        [transactions, pd.DataFrame(household_rows)],
        ignore_index=True,
    )

    transactions = transactions.sort_values(
        ["borrower_id", "date", "transaction_id"]
    ).reset_index(drop=True)

    history_income = transactions[
        transactions["period"].eq("HISTORY")
        & transactions["status"].eq("SUCCESS")
        & transactions["direction"].eq("CREDIT")
        & transactions["category"].eq("BUSINESS_INCOME")
    ]

    median_monthly_income = (
        history_income.groupby(["borrower_id", "month"])[
            "amount_paise"
        ]
        .sum()
        .groupby("borrower_id")
        .median()
    )

    initial_balance = (
        median_monthly_income * 0.25
    ).astype("int64")

    successful = transactions["status"].eq("SUCCESS")

    transactions["signed_amount"] = np.where(
        ~successful,
        0,
        np.where(
            transactions["direction"].eq("CREDIT"),
            transactions["amount_paise"],
            -transactions["amount_paise"],
        ),
    )

    transactions["initial_balance"] = (
        transactions["borrower_id"]
        .map(initial_balance)
        .fillna(0)
        .astype("int64")
    )

    transactions["balance_after_paise"] = (
        transactions["initial_balance"]
        + transactions.groupby("borrower_id")[
            "signed_amount"
        ].cumsum()
    )

    transactions = transactions.drop(
        columns=["signed_amount", "initial_balance"]
    )

    transactions["date"] = transactions["date"].dt.date.astype(str)

    return transactions


def main() -> None:
    transactions = pd.read_csv(TRANSACTIONS_FILE)

    corrected = add_household_expenses_and_balances(
        transactions
    )

    corrected.to_csv(
        TRANSACTIONS_FILE,
        index=False,
    )

    print(
        f"Updated {len(corrected):,} transactions with "
        "household expenses and running balances."
    )


if __name__ == "__main__":
    main()
