from __future__ import annotations

from datetime import date

import pandas as pd

from config import OBSERVATION_MONTHS, OPERATING_INFLOW_CATEGORIES, OPERATING_OUTFLOW_CATEGORIES
from schemas import NormalizedTransaction


def transaction_frame(
    transactions: tuple[NormalizedTransaction, ...] | list[NormalizedTransaction],
    cutoff: str,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Create the leakage-safe eligible transaction frame at a cutoff."""
    cutoff_date = pd.Timestamp(date.fromisoformat(cutoff))
    rows = [item.to_dict() for item in transactions]
    columns = list(NormalizedTransaction.__dataclass_fields__)
    raw = pd.DataFrame(rows, columns=columns)
    if raw.empty:
        return raw.assign(date=pd.Series(dtype="datetime64[ns]")), {
            "raw_transaction_count": 0,
            "duplicate_count": 0,
            "future_transaction_count": 0,
            "eligible_transaction_count": 0,
            "verified_transaction_share": 0.0,
            "unclassified_transaction_share": 0.0,
            "anomalous_transaction_share": 0.0,
            "self_declared_income_share": 0.0,
            "source_count": 0,
        }
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    malformed = int(raw["date"].isna().sum())
    raw = raw.dropna(subset=["date"])
    future_count = int((raw["date"] > cutoff_date).sum())
    raw = raw[raw["date"] <= cutoff_date].copy()
    duplicate_count = int(raw.duplicated("transaction_id", keep="first").sum())
    raw = raw.drop_duplicates("transaction_id", keep="first")
    successful = raw[raw["status"] == "SUCCESS"]
    eligible = successful[successful["model_eligible"]].copy()
    verified_share = float(eligible["verification"].ne("SELF_DECLARED").mean()) if len(eligible) else 0.0
    unclassified_share = float(eligible["category"].eq("UNCLASSIFIED").mean()) if len(eligible) else 0.0
    anomalous_share = float(eligible["anomaly_flag"].mean()) if len(eligible) else 0.0
    credit_total = float(successful.loc[successful["direction"] == "CREDIT", "amount_paise"].sum())
    self_declared = float(
        successful.loc[successful["category"] == "SELF_DECLARED_CASH_INCOME", "amount_paise"].sum()
    )
    return eligible.sort_values(["date", "transaction_id"]).reset_index(drop=True), {
        "raw_transaction_count": int(len(rows)),
        "malformed_transaction_count": malformed,
        "duplicate_count": duplicate_count,
        "future_transaction_count": future_count,
        "eligible_transaction_count": int(len(eligible)),
        "verified_transaction_share": verified_share,
        "unclassified_transaction_share": unclassified_share,
        "anomalous_transaction_share": anomalous_share,
        "self_declared_income_share": self_declared / credit_total if credit_total > 0 else 0.0,
        "source_count": int(eligible["source"].nunique()) if len(eligible) else 0,
    }


def monthly_frame(frame: pd.DataFrame, cutoff: str) -> pd.DataFrame:
    cutoff_period = pd.Period(cutoff, freq="M")
    start_limit = cutoff_period - (OBSERVATION_MONTHS - 1)
    if frame.empty:
        periods = pd.period_range(start_limit, cutoff_period, freq="M")
    else:
        earliest = frame["date"].min().to_period("M")
        periods = pd.period_range(max(earliest, start_limit), cutoff_period, freq="M")
    result = pd.DataFrame(index=periods)
    period = frame["date"].dt.to_period("M") if len(frame) else pd.Series(dtype="period[M]")
    income_mask = (
        frame["direction"].eq("CREDIT")
        & frame["category"].isin(OPERATING_INFLOW_CATEGORIES)
    ) if len(frame) else pd.Series(dtype=bool)
    outflow_mask = (
        frame["direction"].eq("DEBIT")
        & frame["category"].isin(OPERATING_OUTFLOW_CATEGORIES)
    ) if len(frame) else pd.Series(dtype=bool)
    result["inflow"] = frame.loc[income_mask].groupby(period[income_mask])["amount_paise"].sum().reindex(periods, fill_value=0)
    result["outflow"] = frame.loc[outflow_mask].groupby(period[outflow_mask])["amount_paise"].sum().reindex(periods, fill_value=0)
    result["net"] = result["inflow"] - result["outflow"]
    operating_mask = (income_mask | outflow_mask) if len(frame) else pd.Series(dtype=bool)
    result["transaction_count"] = frame.loc[operating_mask].groupby(period[operating_mask]).size().reindex(periods, fill_value=0) if len(frame) else 0
    result["active"] = result["transaction_count"] > 0
    return result.astype({"inflow": float, "outflow": float, "net": float, "transaction_count": int})
