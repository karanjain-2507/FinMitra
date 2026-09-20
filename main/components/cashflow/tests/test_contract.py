from model.inference import CashflowEngine


def test_person4_handoff_contains_required_fields(stable_profile):
    result = CashflowEngine().assess(stable_profile)
    payload = result.to_dict()
    assert set(payload) == {
        "component", "version", "score", "stress_probability", "status",
        "confidence", "features", "reasons", "warnings",
    }
    assert "conservative_monthly_inflow_paise" in payload["features"]
    assert payload["component"] == "cashflow"
    assert payload["status"] in {"SUFFICIENT", "DEGRADED", "INSUFFICIENT"}
    assert payload["stress_probability"] is not None
    assert 0 <= payload["stress_probability"] <= 1
    assert abs(payload["score"] - 100 * (1 - payload["stress_probability"])) <= 0.001
