"""
Deterministic Anomaly Detection.
Provides statistical outlier detection and optional Isolation Forest indicators.
CRITICAL PRINCIPLE: Anomaly != Invalid. Anomalies trigger evidence review and warnings,
never silent record deletion.
"""
from __future__ import annotations
from typing import List, Tuple, Optional
import math
import numpy as np

from ..schemas import NormalizedTransaction
from ..config import (
    RANDOM_SEED,
    ANOMALY_ZSCORE_THRESHOLD,
    ANOMALY_IQR_MULTIPLIER,
    ISOLATION_FOREST_CONTAMINATION,
    ISOLATION_FOREST_MIN_SAMPLES,
)


def detect_anomalies(
    transactions: List[NormalizedTransaction],
    use_isolation_forest: bool = True
) -> Tuple[List[NormalizedTransaction], int]:
    """
    Detect statistical and behavioral transaction anomalies deterministically.
    Updates anomaly_flag and anomaly_score on transactions in-place.
    Returns:
        (transactions, total_anomalies_detected)
    """
    if len(transactions) < 5:
        return transactions, 0

    amounts = np.array([t.amount_paise for t in transactions], dtype=float)
    log_amounts = np.log1p(amounts)

    mean_val = np.mean(amounts)
    std_val = np.std(amounts)
    q25, q75 = np.percentile(amounts, [25, 75])
    iqr = q75 - q25

    anomaly_count = 0

    # 1. Statistical Outlier Detection (Z-Score & IQR)
    z_scores = (amounts - mean_val) / (std_val + 1e-9)
    iqr_upper = q75 + (ANOMALY_IQR_MULTIPLIER * iqr)

    # 2. Optional Isolation Forest if sufficient samples and sklearn is available
    if_scores: Optional[np.ndarray] = None
    if use_isolation_forest and len(transactions) >= ISOLATION_FOREST_MIN_SAMPLES:
        try:
            from sklearn.ensemble import IsolationForest
            # Feature matrix: log_amount, direction (0/1), day of week (0-6)
            feats = []
            for t in transactions:
                dir_val = 1.0 if t.direction == "CREDIT" else 0.0
                dow = float(t.date.weekday())
                feats.append([math.log1p(t.amount_paise), dir_val, dow])
            
            X = np.array(feats)
            iso = IsolationForest(
                contamination=ISOLATION_FOREST_CONTAMINATION,
                random_state=RANDOM_SEED,
                n_estimators=50
            )
            iso.fit(X)
            preds = iso.predict(X)          # -1 for anomaly, 1 for inlier
            raw_scores = iso.score_samples(X)  # lower = more abnormal
            # Normalize scores to 0.0 - 1.0 range (higher = more anomalous)
            min_s, max_s = np.min(raw_scores), np.max(raw_scores)
            if max_s > min_s:
                if_scores = 1.0 - ((raw_scores - min_s) / (max_s - min_s))
            else:
                if_scores = np.zeros(len(transactions))
        except Exception:
            if_scores = None

    for i, txn in enumerate(transactions):
        is_anomaly = False
        score_val = 0.0

        # Check Z-Score
        if abs(z_scores[i]) > ANOMALY_ZSCORE_THRESHOLD:
            is_anomaly = True
            score_val = max(score_val, min(1.0, float(abs(z_scores[i])) / 10.0))

        # Check IQR upper threshold
        if amounts[i] > iqr_upper and iqr > 0:
            is_anomaly = True
            score_val = max(score_val, 0.85)

        # Check Isolation Forest score
        if if_scores is not None and if_scores[i] > 0.80:
            is_anomaly = True
            score_val = max(score_val, float(if_scores[i]))

        if is_anomaly:
            txn.anomaly_flag = True
            txn.anomaly_score = round(score_val, 3)
            anomaly_count += 1
        else:
            txn.anomaly_flag = False
            txn.anomaly_score = 0.0

    return transactions, anomaly_count
