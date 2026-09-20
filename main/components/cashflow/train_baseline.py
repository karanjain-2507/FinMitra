"""Train the original 12-feature Logistic Regression baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import RANDOM_SEED, ROOT
from features.pipeline import FEATURE_NAMES


DATASET_PATH = ROOT / "data" / "processed" / "model_dataset_12.csv"
ARTIFACT_PATH = ROOT / "artifacts" / "cashflow_stress_logistic_baseline_v2.joblib"
METADATA_PATH = ROOT / "artifacts" / "cashflow_stress_logistic_baseline_v2.json"
COEFFICIENTS_PATH = ROOT / "artifacts" / "cashflow_stress_logistic_coefficients_v2.csv"
TARGET = "cashflow_stress_90d"
MODEL_VERSION = "logistic-baseline-2.0.0"
DECISION_THRESHOLD = 0.5


def _target(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)
    normalized = series.astype(str).str.strip().str.lower()
    mapped = normalized.map({"true": 1, "false": 0, "1": 1, "0": 0})
    if mapped.isna().any():
        raise ValueError("cashflow_stress_90d must contain only True/False or 1/0")
    return mapped.astype(int)


def _metrics(y_true: pd.Series, probabilities) -> dict[str, Any]:
    predictions = (probabilities >= DECISION_THRESHOLD).astype(int)
    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])
    return {
        "rows": int(len(y_true)),
        "stress_rate": round(float(y_true.mean()), 6),
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 6),
        "average_precision": round(
            float(average_precision_score(y_true, probabilities)), 6
        ),
        "log_loss": round(float(log_loss(y_true, probabilities)), 6),
        "brier_score": round(float(brier_score_loss(y_true, probabilities)), 6),
        "accuracy_at_0_5": round(float(accuracy_score(y_true, predictions)), 6),
        "precision_at_0_5": round(
            float(precision_score(y_true, predictions, zero_division=0)), 6
        ),
        "recall_at_0_5": round(
            float(recall_score(y_true, predictions, zero_division=0)), 6
        ),
        "f1_at_0_5": round(float(f1_score(y_true, predictions, zero_division=0)), 6),
        "confusion_matrix_at_0_5": matrix.tolist(),
    }


def train_baseline(
    dataset_path: Path = DATASET_PATH,
    artifact_path: Path = ARTIFACT_PATH,
    metadata_path: Path = METADATA_PATH,
    coefficients_path: Path = COEFFICIENTS_PATH,
) -> dict[str, Any]:
    dataset = pd.read_csv(dataset_path)
    required = {"borrower_id", "split", TARGET, *FEATURE_NAMES}
    missing = sorted(required - set(dataset.columns))
    if missing:
        raise ValueError(f"dataset is missing required columns: {missing}")
    if tuple(column for column in dataset.columns if column in FEATURE_NAMES) != FEATURE_NAMES:
        raise ValueError("dataset feature order does not match the locked 12-feature contract")

    dataset[TARGET] = _target(dataset[TARGET])
    splits = {
        name: dataset.loc[dataset["split"].eq(name)].copy()
        for name in ("train", "validation", "test")
    }
    if any(frame.empty for frame in splits.values()):
        raise ValueError("train, validation, and test splits must all be non-empty")
    for name, frame in splits.items():
        if frame[TARGET].nunique() != 2:
            raise ValueError(f"{name} split must contain both stress classes")

    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    random_state=RANDOM_SEED,
                    max_iter=2000,
                    solver="lbfgs",
                ),
            ),
        ]
    )
    train = splits["train"]
    model.fit(train[list(FEATURE_NAMES)], train[TARGET])

    metrics = {}
    for name, frame in splits.items():
        probabilities = model.predict_proba(frame[list(FEATURE_NAMES)])[:, 1]
        metrics[name] = _metrics(frame[TARGET], probabilities)

    classifier = model.named_steps["classifier"]
    coefficient_frame = pd.DataFrame(
        {
            "feature": FEATURE_NAMES,
            "standardized_log_odds_coefficient": classifier.coef_[0],
        }
    ).sort_values("standardized_log_odds_coefficient", ascending=False)

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    coefficients_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "model_version": MODEL_VERSION,
            "feature_names": list(FEATURE_NAMES),
            "target": TARGET,
            "decision_threshold": DECISION_THRESHOLD,
        },
        artifact_path,
    )
    coefficient_frame.to_csv(coefficients_path, index=False)

    metadata = {
        "model_version": MODEL_VERSION,
        "model": "LogisticRegression",
        "purpose": "Baseline probability of cash-flow stress in the next 90 days",
        "target": TARGET,
        "probability_output": "predict_proba(X)[:, 1]",
        "decision_threshold": DECISION_THRESHOLD,
        "random_seed": RANDOM_SEED,
        "synthetic_training_data": True,
        "feature_count": len(FEATURE_NAMES),
        "feature_names": list(FEATURE_NAMES),
        "split_strategy": "Preassigned borrower-level train/validation/test split",
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "metrics": metrics,
        "artifact": artifact_path.name,
        "coefficients": coefficients_path.name,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train the 12-feature cash-flow stress Logistic Regression baseline"
    )
    parser.add_argument("--input", type=Path, default=DATASET_PATH)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--metadata", type=Path, default=METADATA_PATH)
    parser.add_argument("--coefficients", type=Path, default=COEFFICIENTS_PATH)
    args = parser.parse_args()
    metadata = train_baseline(
        args.input, args.artifact, args.metadata, args.coefficients
    )
    print(json.dumps(metadata, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
