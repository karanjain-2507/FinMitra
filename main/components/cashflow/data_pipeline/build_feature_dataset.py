# 2_feature_engineering.py

from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIRECTORY = Path("cashflow_synthetic_data_v2")

TRANSACTIONS_FILE = DATA_DIRECTORY / "transactions.csv"
LABELS_FILE = DATA_DIRECTORY / "labels.csv"
OUTPUT_FILE = DATA_DIRECTORY / "model_dataset.csv"

BUSINESS_EXPENSE_CATEGORIES = {
    "INVENTORY",
    "BUSINESS_ESSENTIAL",
    "UTILITY",
}

VALID_VERIFICATION_LEVELS = {
    "SOURCE_CONNECTED",
    "DOCUMENT_UPLOADED",
    "COUNTERPARTY_CONFIRMED",
}


def safe_ratio(
    numerator: float,
    denominator: float,
) -> float:
    if denominator == 0 or pd.isna(denominator):
        return np.nan

    return float(numerator / denominator)


def complete_month_index(
    borrower_transactions: pd.DataFrame,
) -> pd.PeriodIndex:
    last_month = borrower_transactions["date"].max().to_period("M")

    return pd.period_range(
        end=last_month,
        periods=24,
        freq="M",
    )


def longest_inflow_gap_days(
    inflows: pd.DataFrame,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
) -> int:
    dates = sorted(
        inflows["date"].dt.normalize().drop_duplicates()
    )

    if not dates:
        return int((window_end - window_start).days + 1)

    gaps = [
        max(0, int((dates[0] - window_start).days)),
        max(0, int((window_end - dates[-1]).days)),
    ]

    for previous_date, current_date in zip(
        dates,
        dates[1:],
    ):
        gaps.append(
            max(
                0,
                int((current_date - previous_date).days - 1),
            )
        )

    return max(gaps)


def calculate_balance_buffer(
    transactions: pd.DataFrame,
    monthly_business_expenses: pd.Series,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
) -> float:
    if "balance_after_paise" not in transactions.columns:
        return np.nan

    balances = (
        transactions.sort_values(["date", "transaction_id"])
        .groupby("date")
        .tail(1)
        .set_index("date")["balance_after_paise"]
    )

    daily_index = pd.date_range(
        window_start,
        window_end,
        freq="D",
    )

    daily_balances = (
        balances.reindex(daily_index)
        .ffill()
        .bfill()
    )

    if daily_balances.empty:
        return np.nan

    median_balance = max(
        0,
        float(daily_balances.median()),
    )

    median_monthly_expense = float(
        monthly_business_expenses.median()
    )

    estimated_daily_expense = (
        median_monthly_expense / 30.4375
    )

    return safe_ratio(
        median_balance,
        estimated_daily_expense,
    )


def calculate_features(
    borrower_id: str,
    transactions: pd.DataFrame,
) -> dict:
    transactions = transactions.copy()

    months = complete_month_index(transactions)

    window_start = months[0].start_time.normalize()
    window_end = months[-1].end_time.normalize()

    genuine_income = transactions[
        transactions["status"].eq("SUCCESS")
        & transactions["direction"].eq("CREDIT")
        & transactions["category"].eq("BUSINESS_INCOME")
        & transactions["verification"].isin(
            VALID_VERIFICATION_LEVELS
        )
        & transactions["category_confidence"].ge(0.70)
    ]

    business_expenses = transactions[
        transactions["status"].eq("SUCCESS")
        & transactions["direction"].eq("DEBIT")
        & transactions["category"].isin(
            BUSINESS_EXPENSE_CATEGORIES
        )
    ]

    monthly_income = (
        genuine_income.groupby(
            genuine_income["date"].dt.to_period("M")
        )["amount_paise"]
        .sum()
        .reindex(months, fill_value=0)
        .astype(float)
    )

    monthly_expenses = (
        business_expenses.groupby(
            business_expenses["date"].dt.to_period("M")
        )["amount_paise"]
        .sum()
        .reindex(months, fill_value=0)
        .astype(float)
    )

    monthly_surplus = monthly_income - monthly_expenses

    median_monthly_inflow = float(
        monthly_income.median()
    )

    inflow_mean = float(monthly_income.mean())

    inflow_volatility = safe_ratio(
        float(monthly_income.std(ddof=0)),
        inflow_mean,
    )

    # Replace the existing six-month trend calculation with this bounded formula.
# It prevents low-income seasonal months from creating values like +398%.

    previous_three_months = float(
        monthly_income.iloc[-6:-3].median()
    )

    latest_three_months = float(
        monthly_income.iloc[-3:].median()
    )

    trend_denominator = (
        abs(previous_three_months)
        + abs(latest_three_months)
    ) / 2

    six_month_trend = (
        (latest_three_months - previous_three_months)
        / trend_denominator
        if trend_denominator > 0
        else 0.0
    )

    # The result is bounded between -2 and +2.

    active_days_by_month = (
        genuine_income.assign(
            calculation_month=genuine_income[
                "date"
            ].dt.to_period("M")
        )
        .groupby("calculation_month")["date"]
        .nunique()
        .reindex(months, fill_value=0)
    )

    median_active_earning_days = float(
        active_days_by_month.median()
    )

    total_income = float(
        genuine_income["amount_paise"].sum()
    )

    income_by_customer = genuine_income.groupby(
        "counterparty_id"
    )["amount_paise"].sum()

    largest_customer_income = (
        float(income_by_customer.max())
        if not income_by_customer.empty
        else 0
    )

    income_source_concentration = safe_ratio(
        largest_customer_income,
        total_income,
    )

    customer_month_counts = (
        genuine_income.assign(
            calculation_month=genuine_income[
                "date"
            ].dt.to_period("M")
        )
        .groupby("counterparty_id")[
            "calculation_month"
        ]
        .nunique()
    )

    repeat_customers = customer_month_counts[
        customer_month_counts >= 3
    ].index

    repeat_customer_income = float(
        genuine_income[
            genuine_income["counterparty_id"].isin(
                repeat_customers
            )
        ]["amount_paise"].sum()
    )

    repeat_customer_ratio = safe_ratio(
        repeat_customer_income,
        total_income,
    )

    first_year = monthly_income.iloc[:12].to_numpy()
    second_year = monthly_income.iloc[12:].to_numpy()

    year_on_year_deviation = np.abs(
        second_year - first_year
    ) / np.maximum(first_year, 1)

    seasonality_adjusted_stability = float(
        np.clip(
            1 - np.median(year_on_year_deviation),
            0,
            1,
        )
    )

    median_operating_surplus = float(
        monthly_surplus.median()
    )

    negative_cashflow_month_ratio = float(
        (monthly_surplus < 0).mean()
    )

    expense_mean = float(
        monthly_expenses.mean()
    )

    expense_volatility = safe_ratio(
        float(monthly_expenses.std(ddof=0)),
        expense_mean,
    )

    balance_buffer_days = calculate_balance_buffer(
        transactions,
        monthly_expenses,
        window_start,
        window_end,
    )

    longest_gap = longest_inflow_gap_days(
        genuine_income,
        window_start,
        window_end,
    )

    return {
        "borrower_id": borrower_id,
        "median_monthly_business_inflow_paise": (
            median_monthly_inflow
        ),
        "inflow_volatility": inflow_volatility,
        "six_month_inflow_trend": six_month_trend,
        "longest_inflow_gap_days": longest_gap,
        "median_active_earning_days": (
            median_active_earning_days
        ),
        "income_source_concentration": (
            income_source_concentration
        ),
        "repeat_customer_ratio": repeat_customer_ratio,
        "seasonality_adjusted_stability": (
            seasonality_adjusted_stability
        ),
        "median_operating_surplus_paise": (
            median_operating_surplus
        ),
        "negative_cashflow_month_ratio": (
            negative_cashflow_month_ratio
        ),
        "expense_volatility": expense_volatility,
        "balance_buffer_days": balance_buffer_days,
    }


def main() -> None:
    transactions = pd.read_csv(
        TRANSACTIONS_FILE,
        parse_dates=["date"],
    )

    labels = pd.read_csv(LABELS_FILE)

    historical_transactions = transactions[
        transactions["period"].eq("HISTORY")
    ].copy()

    feature_rows = []

    for borrower_id, borrower_transactions in (
        historical_transactions.groupby("borrower_id")
    ):
        feature_rows.append(
            calculate_features(
                borrower_id,
                borrower_transactions,
            )
        )

    features = pd.DataFrame(feature_rows)

    model_dataset = features.merge(
        labels[
            [
                "borrower_id",
                "split",
                "cashflow_stress_90d",
            ]
        ],
        on="borrower_id",
        how="inner",
        validate="one_to_one",
    )

    feature_columns = [
        column
        for column in model_dataset.columns
        if column
        not in {
            "borrower_id",
            "split",
            "cashflow_stress_90d",
        }
    ]

    if model_dataset[feature_columns].isna().any().any():
        print("Warning: some features contain missing values:")
        print(
            model_dataset[feature_columns]
            .isna()
            .sum()
            .loc[lambda values: values > 0]
        )

    model_dataset.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(
        f"Created {OUTPUT_FILE} with "
        f"{len(model_dataset):,} borrowers."
    )

    print(
        f"Stress rate: "
        f"{model_dataset['cashflow_stress_90d'].mean():.2%}"
    )

    print("\nFeature summary:")
    print(
        model_dataset[feature_columns]
        .describe()
        .transpose()
    )


if __name__ == "__main__":
    main()
