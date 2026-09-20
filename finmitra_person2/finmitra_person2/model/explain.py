from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

from features.pipeline import FEATURE_NAMES
from schemas import Reason

FEATURE_REASON = {
    "inflow_cv": ("CF01", "CF02", "Business inflow stability affected the cash-flow health prediction."),
    "median_monthly_net": ("CF03", "CF04", "Operating surplus affected the cash-flow health prediction."),
    "net_cashflow_trend": ("CF05", "CF06", "The operating cash-flow trend affected the prediction."),
    "recent_vs_previous_inflow": ("CF10", "CF11", "Recent inflow compared with the preceding period affected the prediction."),
    "outflow_cv": ("CF03", "CF12", "Operating-expense variation affected the prediction."),
    "negative_net_month_rate": ("CF03", "CF13", "The frequency of negative operating months affected the prediction."),
    "seasonality_strength": ("CF08", "CF09", "The predictability of seasonal cash flow affected the prediction."),
    "verified_transaction_share": ("CF16", "CF17", "The share of corroborated transaction history affected assessment support."),
}


def local_sensitivity(model, values: np.ndarray, reference: np.ndarray, limit: int = 5) -> list[Reason]:
    base_frame = pd.DataFrame([values], columns=FEATURE_NAMES)
    base = float(np.clip(model.predict(base_frame)[0], 0, 100))
    contributions: list[tuple[str, float]] = []
    for index, name in enumerate(FEATURE_NAMES):
        changed = values.copy()
        changed[index] = reference[index]
        neutral = float(np.clip(model.predict(pd.DataFrame([changed], columns=FEATURE_NAMES))[0], 0, 100))
        contributions.append((name, base - neutral))
    selected = sorted(contributions, key=lambda item: abs(item[1]), reverse=True)[:limit]
    reasons = []
    for name, impact in selected:
        positive_code, negative_code, message = FEATURE_REASON.get(
            name, ("CF18", "CF19", f"{name.replace('_', ' ').title()} affected the model prediction.")
        )
        reasons.append(Reason(
            code=positive_code if impact >= 0 else negative_code,
            direction="POSITIVE" if impact >= 0 else "NEGATIVE",
            impact=round(float(impact), 3),
            message=message,
        ))
    return reasons


def global_importance_frame(feature_names, importances):
    return pd.DataFrame({"feature": feature_names, "importance": importances}).sort_values(
        "importance", ascending=False
    )
