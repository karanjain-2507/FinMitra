from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline

from config import (
    ARTIFACT_PATH, DATASET_PATH, FEATURE_VERSION, GLOBAL_IMPORTANCE_PATH,
    METADATA_PATH, MODEL_VERSION, RANDOM_SEED, TRAINING_MATRIX_PATH,
)
from features.pipeline import FEATURE_NAMES, build_features
from model.artifact import save_versioned_artifact
from model.evaluate import regression_metrics
from schemas import NormalizedTransaction


def load_training_matrix(path: Path = DATASET_PATH) -> pd.DataFrame:
    rows = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            transactions = tuple(NormalizedTransaction.from_dict(item) for item in record["transactions"])
            vector = build_features(transactions, record["as_of_date"])
            rows.append({
                "borrower_id": record["borrower_id"],
                "archetype": record["archetype"],
                "split": record["split"],
                "target_cashflow_health": float(record["target_cashflow_health"]),
                **vector.values,
            })
    matrix = pd.DataFrame(rows)
    TRAINING_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(TRAINING_MATRIX_PATH, index=False)
    return matrix


def _model() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("regressor", HistGradientBoostingRegressor(
            learning_rate=.055,
            max_iter=240,
            max_leaf_nodes=15,
            min_samples_leaf=16,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=RANDOM_SEED,
        )),
    ])


def train_model(dataset_path: Path = DATASET_PATH) -> dict:
    matrix = load_training_matrix(dataset_path)
    train = matrix[matrix["split"] == "train"]
    validation = matrix[matrix["split"] == "validation"]
    test = matrix[matrix["split"] == "test"]
    x_train, y_train = train[list(FEATURE_NAMES)], train["target_cashflow_health"]
    x_validation, y_validation = validation[list(FEATURE_NAMES)], validation["target_cashflow_health"]
    x_test, y_test = test[list(FEATURE_NAMES)], test["target_cashflow_health"]
    baseline = DummyRegressor(strategy="mean").fit(x_train, y_train)
    primary = _model().fit(x_train, y_train)
    validation_predictions = np.clip(primary.predict(x_validation), 0, 100)
    test_predictions = np.clip(primary.predict(x_test), 0, 100)
    metrics = {
        "baseline_validation": regression_metrics(y_validation, baseline.predict(x_validation)),
        "primary_validation": regression_metrics(y_validation, validation_predictions),
        "baseline_test": regression_metrics(y_test, baseline.predict(x_test)),
        "primary_test": regression_metrics(y_test, test_predictions),
    }
    importance = permutation_importance(
        primary, x_test, y_test, n_repeats=8, random_state=RANDOM_SEED, scoring="neg_mean_absolute_error"
    )
    importance_frame = pd.DataFrame({
        "feature": FEATURE_NAMES,
        "importance": importance.importances_mean,
    }).sort_values("importance", ascending=False)
    GLOBAL_IMPORTANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    importance_frame.to_csv(GLOBAL_IMPORTANCE_PATH, index=False)
    reference = x_train.median().to_numpy(dtype=float)
    quantiles = {
        name: {"p01": float(x_train[name].quantile(.01)), "p99": float(x_train[name].quantile(.99))}
        for name in FEATURE_NAMES
    }
    dataset_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    metadata = {
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "training_row_count": int(len(train)),
        "validation_row_count": int(len(validation)),
        "test_row_count": int(len(test)),
        "borrower_count": int(matrix["borrower_id"].nunique()),
        "feature_count": len(FEATURE_NAMES),
        "feature_list": list(FEATURE_NAMES),
        "dataset_sha256": dataset_hash,
        "model": "HistGradientBoostingRegressor",
        "baseline": "DummyRegressor(mean)",
        "target_definition": "0.35 future surplus margin + 0.25 future inflow stability + 0.20 positive-net month rate + 0.20 future net trend; clamped 0-100",
        "split_strategy": "borrower-disjoint 70/15/15; every row uses a chronological 24-month observation window followed by a three-month target window",
        "metrics": metrics,
        "synthetic_training_data": True,
    }
    payload = {
        "model": primary,
        "reference": reference,
        "feature_names": list(FEATURE_NAMES),
        "feature_version": FEATURE_VERSION,
        "model_version": MODEL_VERSION,
        "training_quantiles": quantiles,
        "metadata": metadata,
    }
    save_versioned_artifact(payload, ARTIFACT_PATH, metadata, METADATA_PATH)
    return metadata
