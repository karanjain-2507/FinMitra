from __future__ import annotations

import numpy as np
import pandas as pd


def normalized_trend(values: pd.Series) -> float:
    array = values.to_numpy(dtype=float)
    if len(array) < 2:
        return 0.0
    scale = max(float(np.median(np.abs(array))), 1.0)
    slope = float(np.polyfit(np.arange(len(array), dtype=float), array, 1)[0])
    return float(np.clip(slope / scale, -2.0, 2.0))


def recent_change(values: pd.Series) -> float:
    if len(values) < 6:
        return 0.0
    previous = float(values.iloc[-6:-3].median())
    recent = float(values.iloc[-3:].median())
    denominator = (abs(previous) + abs(recent)) / 2.0
    return float(np.clip((recent - previous) / denominator, -2.0, 2.0)) if denominator else 0.0
