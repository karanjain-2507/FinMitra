"""
Unit tests for confidence computation: bounds, scaling, penalties.
"""
from __future__ import annotations
import pytest

from finmitra_person1.evidence.confidence import compute_evidence_confidence


def test_confidence_is_strictly_bounded():
    features = {
        "coverage_days": 180,
        "source_count": 4,
        "total_transactions": 50,
        "corroboration_rate": 0.80,
        "verified_ratio": 0.90
    }
    conf = compute_evidence_confidence(features, evidence_score=92.0, insufficient_history=False, conflict_count=0)
    assert 0.0 <= conf <= 1.0
    assert conf >= 0.70


def test_confidence_penalized_on_insufficient_history():
    features = {
        "coverage_days": 20,
        "source_count": 1,
        "total_transactions": 8,
        "corroboration_rate": 0.0,
        "verified_ratio": 0.0
    }
    conf = compute_evidence_confidence(features, evidence_score=35.0, insufficient_history=True, conflict_count=0)
    assert 0.0 <= conf <= 1.0
    assert conf <= 0.45  # Must be capped under 0.45 when history is insufficient
