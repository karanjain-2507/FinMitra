"""The original, locked 12-feature cash-flow calculation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from config import FEATURE_VERSION, OBSERVATION_MONTHS, OPERATING_OUTFLOW_CATEGORIES
from features.aggregation import transaction_frame
from features.quality import active_months, data_coverage
from schemas import BorrowerInput, NormalizedTransaction


FEATURE_NAMES = (
    "median_monthly_business_inflow_paise",
    "inflow_volatility",
    "six_month_inflow_trend",
    "longest_inflow_gap_days",
    "median_active_earning_days",
    "income_source_concentration",
    "repeat_customer_ratio",
    "seasonality_adjusted_stability",
    "median_operating_surplus_paise",
    "negative_cashflow_month_ratio",
    "expense_volatility",
    "balance_buffer_days",
)

VERIFIED_INCOME_LEVELS = frozenset(
    {
        "SOURCE_CONNECTED",
        "CROSS_SOURCE_CORROBORATED",
        "DOCUMENT_MATCHED",
        "LEDGER_MATCHED",
        "MERCHANT_MATCHED",
        "DOCUMENT_UPLOADED",
        "COUNTERPARTY_CONFIRMED",
    }
)

BUSINESS_EXPENSE_CATEGORIES = frozenset(
    set(OPERATING_OUTFLOW_CATEGORIES)
    | {"INVENTORY", "BUSINESS_ESSENTIAL", "UTILITY"}
)


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0 or pd.isna(denominator):
        return None
    return float(numerator / denominator)


@dataclass(frozen=True)
class FeatureVector:
    version: str
    values: dict[str, float | None]
    context: dict[str, Any]

    def model_values(self) -> list[float]:
        return [
            np.nan if self.values[name] is None else float(self.values[name])
            for name in FEATURE_NAMES
        ]


def _longest_inflow_gap_days(
    inflows: pd.DataFrame,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
) -> int:
    dates = sorted(inflows["date"].dt.normalize().drop_duplicates())
    if not dates:
        return int((window_end - window_start).days + 1)
    gaps = [
        max(0, int((dates[0] - window_start).days)),
        max(0, int((window_end - dates[-1]).days)),
    ]
    gaps.extend(
        max(0, int((current - previous).days - 1))
        for previous, current in zip(dates, dates[1:])
    )
    return max(gaps)


def _balance_buffer_days(
    all_transactions: pd.DataFrame,
    monthly_expenses: pd.Series,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
) -> float | None:
    if "balance_after_paise" not in all_transactions or all_transactions.empty:
        return None
    with_balance = all_transactions.dropna(subset=["balance_after_paise"])
    if with_balance.empty:
        return None
    balances = (
        with_balance.sort_values(["date", "transaction_id"])
        .groupby("date")
        .tail(1)
        .set_index("date")["balance_after_paise"]
    )
    daily_balances = (
        balances.reindex(pd.date_range(window_start, window_end, freq="D"))
        .ffill()
        .bfill()
    )
    if daily_balances.empty:
        return None
    median_balance = max(0.0, float(daily_balances.median()))
    estimated_daily_expense = float(monthly_expenses.median()) / 30.4375
    return _safe_ratio(median_balance, estimated_daily_expense)


def _raw_frame(
    transactions: tuple[NormalizedTransaction, ...] | list[NormalizedTransaction],
    cutoff: str,
) -> pd.DataFrame:
    rows = [item.to_dict() for item in transactions]
    frame = pd.DataFrame(rows, columns=list(NormalizedTransaction.__dataclass_fields__))
    if frame.empty:
        return frame.assign(date=pd.Series(dtype="datetime64[ns]"))
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    cutoff_date = pd.Timestamp(date.fromisoformat(cutoff))
    return (
        frame.dropna(subset=["date"])
        .loc[lambda values: values["date"] <= cutoff_date]
        .drop_duplicates("transaction_id", keep="first")
        .sort_values(["date", "transaction_id"])
        .reset_index(drop=True)
    )


def build_features(
    transactions: tuple[NormalizedTransaction, ...] | list[NormalizedTransaction],
    cutoff: str,
) -> FeatureVector:
    eligible, quality = transaction_frame(transactions, cutoff)
    all_transactions = _raw_frame(transactions, cutoff)

    cutoff_period = pd.Period(cutoff, freq="M")
    months = pd.period_range(end=cutoff_period, periods=OBSERVATION_MONTHS, freq="M")
    window_start = months[0].start_time.normalize()
    window_end = min(
        months[-1].end_time.normalize(),
        pd.Timestamp(date.fromisoformat(cutoff)),
    )

    genuine_income = eligible[
        eligible["direction"].eq("CREDIT")
        & eligible["category"].eq("BUSINESS_INCOME")
        & eligible["verification"].isin(VERIFIED_INCOME_LEVELS)
        & eligible["category_confidence"].ge(0.70)
    ].copy()
    business_expenses = eligible[
        eligible["direction"].eq("DEBIT")
        & eligible["category"].isin(BUSINESS_EXPENSE_CATEGORIES)
    ].copy()

    income_period = genuine_income["date"].dt.to_period("M")
    expense_period = business_expenses["date"].dt.to_period("M")
    monthly_income = (
        genuine_income.groupby(income_period)["amount_paise"]
        .sum()
        .reindex(months, fill_value=0)
        .astype(float)
    )
    monthly_expenses = (
        business_expenses.groupby(expense_period)["amount_paise"]
        .sum()
        .reindex(months, fill_value=0)
        .astype(float)
    )
    monthly_surplus = monthly_income - monthly_expenses

    previous_three = float(monthly_income.iloc[-6:-3].median())
    latest_three = float(monthly_income.iloc[-3:].median())
    trend_denominator = (abs(previous_three) + abs(latest_three)) / 2
    six_month_trend = (
        (latest_three - previous_three) / trend_denominator
        if trend_denominator > 0
        else 0.0
    )

    active_days_by_month = (
        genuine_income.assign(calculation_month=income_period)
        .groupby("calculation_month")["date"]
        .nunique()
        .reindex(months, fill_value=0)
    )
    total_income = float(genuine_income["amount_paise"].sum())
    income_by_customer = genuine_income.groupby("counterparty")["amount_paise"].sum()
    largest_customer_income = (
        float(income_by_customer.max()) if not income_by_customer.empty else 0.0
    )
    customer_month_counts = (
        genuine_income.assign(calculation_month=income_period)
        .groupby("counterparty")["calculation_month"]
        .nunique()
    )
    repeat_customers = customer_month_counts[customer_month_counts >= 3].index
    repeat_customer_income = float(
        genuine_income[genuine_income["counterparty"].isin(repeat_customers)][
            "amount_paise"
        ].sum()
    )

    first_year = monthly_income.iloc[:12].to_numpy()
    second_year = monthly_income.iloc[12:].to_numpy()
    year_on_year_deviation = np.abs(second_year - first_year) / np.maximum(
        first_year, 1
    )
    seasonality_adjusted_stability = float(
        np.clip(1 - np.median(year_on_year_deviation), 0, 1)
    )

    operating = pd.concat([genuine_income, business_expenses], ignore_index=True)
    operating_count_by_month = (
        operating.assign(
            calculation_month=lambda values: values["date"].dt.to_period("M")
        )
        .groupby("calculation_month")
        .size()
        .reindex(months, fill_value=0)
    )
    monthly_context = pd.DataFrame(
        {
            "transaction_count": operating_count_by_month.astype(int),
            "active": operating_count_by_month.gt(0),
        },
        index=months,
    )

    values: dict[str, float | None] = {
        "median_monthly_business_inflow_paise": float(monthly_income.median()),
        "inflow_volatility": _safe_ratio(
            float(monthly_income.std(ddof=0)), float(monthly_income.mean())
        ),
        "six_month_inflow_trend": float(np.clip(six_month_trend, -2.0, 2.0)),
        "longest_inflow_gap_days": float(
            _longest_inflow_gap_days(genuine_income, window_start, window_end)
        ),
        "median_active_earning_days": float(active_days_by_month.median()),
        "income_source_concentration": _safe_ratio(
            largest_customer_income, total_income
        ),
        "repeat_customer_ratio": _safe_ratio(repeat_customer_income, total_income),
        "seasonality_adjusted_stability": seasonality_adjusted_stability,
        "median_operating_surplus_paise": float(monthly_surplus.median()),
        "negative_cashflow_month_ratio": float((monthly_surplus < 0).mean()),
        "expense_volatility": _safe_ratio(
            float(monthly_expenses.std(ddof=0)), float(monthly_expenses.mean())
        ),
        "balance_buffer_days": _balance_buffer_days(
            all_transactions, monthly_expenses, window_start, window_end
        ),
    }
    context = {
        **quality,
        "active_months": active_months(monthly_context),
        "operating_transaction_count": int(operating_count_by_month.sum()),
        "observed_months": OBSERVATION_MONTHS,
        "data_coverage": data_coverage(monthly_context),
        "conservative_monthly_inflow": float(
            monthly_income[monthly_income > 0].quantile(0.25)
            if (monthly_income > 0).any()
            else 0.0
        ),
        "median_monthly_business_expense_paise": float(
            monthly_expenses[monthly_expenses > 0].median()
            if (monthly_expenses > 0).any()
            else 0.0
        ),
        "cutoff": cutoff,
    }
    return FeatureVector(FEATURE_VERSION, values, context)


def build_features_for_profile(profile: BorrowerInput) -> FeatureVector:
    return build_features(profile.transactions, profile.as_of_date)
