from __future__ import annotations

import pandas as pd


def active_months(monthly: pd.DataFrame) -> int:
    return int(monthly["active"].sum())


def data_coverage(monthly: pd.DataFrame) -> float:
    return float(monthly["active"].mean()) if len(monthly) else 0.0
