"""
Integration tests executing the pipeline on all 4 canonical synthetic fixtures.
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from finmitra_person1.schemas import BorrowerInput
from finmitra_person1.evidence.engine import EvidenceEngine


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_strong_borrower_fixture():
    path = FIXTURES_DIR / "strong_borrower" / "input.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    borrower = BorrowerInput.model_validate(data)
    engine = EvidenceEngine()
    bundle = engine.process(borrower)

    assert bundle.result.evidence_grade in ("A", "B")
    assert bundle.result.status == "SUFFICIENT"
    assert bundle.result.insufficient_history is False
    assert bundle.result.confidence >= 0.70
    assert len(bundle.conflicts) == 0
    assert len(bundle.normalized_transactions) > 20


def test_seasonal_farmer_fixture():
    path = FIXTURES_DIR / "seasonal_farmer" / "input.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    borrower = BorrowerInput.model_validate(data)
    engine = EvidenceEngine()
    bundle = engine.process(borrower)

    assert bundle.result.evidence_grade in ("A", "B")
    assert bundle.result.status == "SUFFICIENT"
    assert bundle.result.insufficient_history is False
    assert len(bundle.normalized_transactions) >= 25


def test_thin_file_fixture():
    path = FIXTURES_DIR / "thin_file" / "input.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    borrower = BorrowerInput.model_validate(data)
    engine = EvidenceEngine()
    bundle = engine.process(borrower)

    assert bundle.result.insufficient_history is True
    assert bundle.result.status == "INSUFFICIENT"
    assert bundle.result.confidence <= 0.45


def test_messy_multi_source_fixture():
    path = FIXTURES_DIR / "messy_multi_source" / "input.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    borrower = BorrowerInput.model_validate(data)
    engine = EvidenceEngine()
    bundle = engine.process(borrower)

    # Must detect material conflicts
    assert len(bundle.conflicts) >= 1

    # Must have self-declared cash income properly tagged and model_eligible=False
    self_decl = [t for t in bundle.normalized_transactions if t.category == "SELF_DECLARED_CASH_INCOME"]
    assert len(self_decl) == 1
    assert self_decl[0].model_eligible is False

    # Must flag anomaly without deleting
    anomalies = [t for t in bundle.normalized_transactions if t.anomaly_flag is True]
    assert len(anomalies) >= 1
