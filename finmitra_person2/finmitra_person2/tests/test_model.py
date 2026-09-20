import json

from config import ARTIFACT_PATH, METADATA_PATH
from features.pipeline import FEATURE_NAMES
from model.artifact import load_artifact
from model.inference import CashflowEngine


def test_artifact_loads_and_is_versioned():
    artifact = load_artifact(ARTIFACT_PATH)
    assert artifact["model_version"] == "hist-gradient-boosting-2.0.0"
    assert tuple(artifact["feature_names"]) == FEATURE_NAMES
    assert hasattr(artifact["model"], "predict_proba")


def test_prediction_is_bounded_and_deterministic(stable_profile):
    engine = CashflowEngine()
    first = engine.assess(stable_profile)
    second = engine.assess(stable_profile)
    assert first == second
    assert first.score is not None and 0 <= first.score <= 100
    assert first.stress_probability is not None
    assert 0 <= first.stress_probability <= 1
    assert abs(first.score - 100 * (1 - first.stress_probability)) <= 0.001
    assert 0 <= first.confidence <= 1


def test_thin_file_is_insufficient(thin_profile):
    result = CashflowEngine().assess(thin_profile)
    assert result.status == "INSUFFICIENT"
    assert result.score is None
    assert result.stress_probability is None
    assert {reason.code for reason in result.reasons} >= {"CF14", "CF15"}


def test_metadata_reports_classifier_holdout_metrics():
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["feature_count"] == 12
    assert metadata["metrics"]["test"]["roc_auc"] >= 0.596
    assert metadata["metrics"]["test"]["rows"] > 0


def test_local_explanations_are_cashflow_scoped(stable_profile):
    result = CashflowEngine().assess(stable_profile)
    assert result.reasons
    assert all(reason.code.startswith("CF") for reason in result.reasons)
    assert all(reason.direction in {"POSITIVE", "NEGATIVE", "NEUTRAL"} for reason in result.reasons)
