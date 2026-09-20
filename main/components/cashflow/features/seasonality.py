from __future__ import annotations

import numpy as np
import pandas as pd


def seasonality_features(values: pd.Series) -> dict[str, float]:
    array = values.to_numpy(dtype=float)
    positive = array[array > 0]
    peak_to_trough = float(np.max(positive) / max(np.min(positive), 1.0)) if len(positive) else 0.0
    if len(array) < 18 or np.mean(array) <= 0 or np.std(array) / np.mean(array) < 0.08:
        return {"seasonality_strength": 0.0, "peak_to_trough_ratio": peak_to_trough, "seasonal_recovery_rate": 0.0}
    left, right = array[:-12], array[12:]
    correlation = float(np.corrcoef(left, right)[0, 1]) if np.std(left) > 0 and np.std(right) > 0 else 0.0
    strength = float(np.clip(correlation, 0.0, 1.0))
    low_index = int(np.argmin(array[:-3])) if len(array) > 3 else 0
    future_slice = array[low_index + 1 : min(low_index + 4, len(array))]
    recovery = float(np.max(future_slice) / max(array[low_index], 1.0)) if len(future_slice) else 0.0
    return {
        "seasonality_strength": strength,
        "peak_to_trough_ratio": float(np.clip(peak_to_trough, 0.0, 20.0)),
        "seasonal_recovery_rate": float(np.clip(recovery, 0.0, 20.0)),
    }
