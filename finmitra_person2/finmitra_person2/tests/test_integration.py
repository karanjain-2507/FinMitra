import json

from config import METADATA_PATH, ROOT
from model.inference import CashflowEngine
from schemas import BorrowerInput


def _fixture(name: str) -> BorrowerInput:
    raw = json.loads((ROOT / "fixtures" / name / "input.json").read_text(encoding="utf-8"))
    return BorrowerInput.from_dict(raw)


def test_fixtures_produce_the_probability_contract():
    engine = CashflowEngine()
    results = [
        engine.assess(_fixture("stable_kirana")),
        engine.assess(_fixture("declining_business")),
        engine.assess(_fixture("seasonal_farmer")),
    ]
    for result in results:
        assert result.score is not None
        assert result.stress_probability is not None
        assert 0 <= result.stress_probability <= 1
        assert abs(result.score - 100 * (1 - result.stress_probability)) <= 0.001


def test_trained_model_meets_the_recorded_stop_threshold():
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["feature_count"] == 12
    assert metadata["purpose"] == "Probability of cash-flow stress in the next 90 days"
    assert metadata["metrics"]["test"]["roc_auc"] >= 0.596
