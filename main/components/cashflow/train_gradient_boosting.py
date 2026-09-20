"""Train the 12-feature HistGradientBoosting cash-flow stress classifier."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from config import RANDOM_SEED, ROOT
from features.pipeline import FEATURE_NAMES
from train_baseline import DATASET_PATH, TARGET, _metrics, _target


ARTIFACT_PATH = ROOT / "artifacts" / "cashflow_stress_hist_gradient_boosting_v2.joblib"
METADATA_PATH = ROOT / "artifacts" / "cashflow_stress_hist_gradient_boosting_v2.json"
SEARCH_RESULTS_PATH = ROOT / "artifacts" / "cashflow_stress_hist_gradient_boosting_search_v2.csv"
MODEL_VERSION = "hist-gradient-boosting-2.0.0"


def _pipeline(parameters: dict[str, Any]) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                HistGradientBoostingClassifier(
                    loss="log_loss",
                    early_stopping=False,
                    random_state=RANDOM_SEED,
                    **parameters,
                ),
            ),
        ]
    )


def _candidates() -> list[dict[str, Any]]:
    return [
        {
            "learning_rate": learning_rate,
            "max_iter": max_iter,
            "max_leaf_nodes": max_leaf_nodes,
            "min_samples_leaf": min_samples_leaf,
            "l2_regularization": l2_regularization,
        }
        for (
            learning_rate,
            max_iter,
            max_leaf_nodes,
            min_samples_leaf,
            l2_regularization,
        ) in itertools.product(
            (0.03, 0.06),
            (100, 200),
            (7, 15),
            (10, 20, 30),
            (0.0, 1.0),
        )
    ]


def train_gradient_boosting(
    dataset_path: Path = DATASET_PATH,
    artifact_path: Path = ARTIFACT_PATH,
    metadata_path: Path = METADATA_PATH,
    search_results_path: Path = SEARCH_RESULTS_PATH,
) -> dict[str, Any]:
    dataset = pd.read_csv(dataset_path)
    required = {"borrower_id", "split", TARGET, *FEATURE_NAMES}
    missing = sorted(required - set(dataset.columns))
    if missing:
        raise ValueError(f"dataset is missing required columns: {missing}")
    dataset[TARGET] = _target(dataset[TARGET])

    train = dataset.loc[dataset["split"].eq("train")].copy()
    validation = dataset.loc[dataset["split"].eq("validation")].copy()
    test = dataset.loc[dataset["split"].eq("test")].copy()
    if any(frame.empty for frame in (train, validation, test)):
        raise ValueError("train, validation, and test splits must all be non-empty")

    search_rows = []
    best_parameters = None
    best_validation_metrics = None
    best_key = None
    for parameters in _candidates():
        candidate = _pipeline(parameters)
        candidate.fit(train[list(FEATURE_NAMES)], train[TARGET])
        probabilities = candidate.predict_proba(validation[list(FEATURE_NAMES)])[:, 1]
        metrics = _metrics(validation[TARGET], probabilities)
        search_rows.append({**parameters, **metrics})
        selection_key = (
            metrics["roc_auc"],
            metrics["average_precision"],
            -metrics["brier_score"],
        )
        if best_key is None or selection_key > best_key:
            best_key = selection_key
            best_parameters = parameters
            best_validation_metrics = metrics

    assert best_parameters is not None and best_validation_metrics is not None
    development = pd.concat([train, validation], ignore_index=True)
    final_model = _pipeline(best_parameters)
    final_model.fit(development[list(FEATURE_NAMES)], development[TARGET])
    development_probabilities = final_model.predict_proba(
        development[list(FEATURE_NAMES)]
    )[:, 1]
    test_probabilities = final_model.predict_proba(test[list(FEATURE_NAMES)])[:, 1]

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    search_results_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(search_rows).sort_values(
        ["roc_auc", "average_precision", "brier_score"],
        ascending=[False, False, True],
    ).to_csv(search_results_path, index=False)
    joblib.dump(
        {
            "model": final_model,
            "model_version": MODEL_VERSION,
            "feature_names": list(FEATURE_NAMES),
            "target": TARGET,
            "best_parameters": best_parameters,
            "decision_threshold": 0.5,
        },
        artifact_path,
    )

    metadata = {
        "model_version": MODEL_VERSION,
        "model": "HistGradientBoostingClassifier",
        "purpose": "Probability of cash-flow stress in the next 90 days",
        "target": TARGET,
        "probability_output": "predict_proba(X)[:, 1]",
        "random_seed": RANDOM_SEED,
        "synthetic_training_data": True,
        "feature_count": len(FEATURE_NAMES),
        "feature_names": list(FEATURE_NAMES),
        "selection": (
            "48 fixed candidates; highest validation ROC-AUC, then average "
            "precision, then lowest Brier score"
        ),
        "best_parameters": best_parameters,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "metrics": {
            "validation_during_selection": best_validation_metrics,
            "development_after_refit": _metrics(
                development[TARGET], development_probabilities
            ),
            "test": _metrics(test[TARGET], test_probabilities),
        },
        "artifact": artifact_path.name,
        "search_results": search_results_path.name,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train the 12-feature HistGradientBoosting stress classifier"
    )
    parser.add_argument("--input", type=Path, default=DATASET_PATH)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--metadata", type=Path, default=METADATA_PATH)
    parser.add_argument("--search-results", type=Path, default=SEARCH_RESULTS_PATH)
    args = parser.parse_args()
    metadata = train_gradient_boosting(
        args.input, args.artifact, args.metadata, args.search_results
    )
    print(json.dumps(metadata, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
