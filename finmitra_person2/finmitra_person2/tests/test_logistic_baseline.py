from __future__ import annotations

import joblib

from features.pipeline import FEATURE_NAMES
from train_baseline import DATASET_PATH, train_baseline


def test_logistic_baseline_uses_only_original_12_features(tmp_path):
    artifact_path = tmp_path / "baseline.joblib"
    metadata = train_baseline(
        DATASET_PATH,
        artifact_path,
        tmp_path / "metadata.json",
        tmp_path / "coefficients.csv",
    )
    artifact = joblib.load(artifact_path)
    assert metadata["feature_count"] == 12
    assert tuple(metadata["feature_names"]) == FEATURE_NAMES
    assert tuple(artifact["feature_names"]) == FEATURE_NAMES
    assert set(metadata["metrics"]) == {"train", "validation", "test"}
    for split in metadata["metrics"].values():
        assert 0 <= split["roc_auc"] <= 1
        assert 0 <= split["brier_score"] <= 1
