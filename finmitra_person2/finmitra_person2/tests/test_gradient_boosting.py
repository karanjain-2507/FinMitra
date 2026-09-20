from __future__ import annotations

import joblib

from features.pipeline import FEATURE_NAMES
from train_baseline import DATASET_PATH
from train_gradient_boosting import train_gradient_boosting


def test_gradient_boosting_uses_locked_features_and_probability_output(tmp_path):
    artifact_path = tmp_path / "gradient.joblib"
    metadata = train_gradient_boosting(
        DATASET_PATH,
        artifact_path,
        tmp_path / "metadata.json",
        tmp_path / "search.csv",
    )
    artifact = joblib.load(artifact_path)
    assert metadata["feature_count"] == 12
    assert tuple(artifact["feature_names"]) == FEATURE_NAMES
    assert 0 <= metadata["metrics"]["test"]["roc_auc"] <= 1
    assert 0 <= metadata["metrics"]["test"]["brier_score"] <= 1
