"""
Unit tests for evidence quality scoring and grading policy.
"""
from __future__ import annotations
import pytest

from finmitra_person1.evidence.grading import compute_evidence_score, determine_grade, check_insufficient_history


def test_high_quality_evidence_scoring():
    features = {
        "source_count": 4,
        "total_transactions": 50,
        "verified_transaction_count": 45,
        "unclassified_transaction_count": 2,
        "corroborated_count": 25,
        "coverage_days": 180,
    }
    score, breakdown = compute_evidence_score(features, conflict_count=0, raw_error_count=0)
    assert score >= 85.0
    assert determine_grade(score) == "A"


def test_conflict_penalizes_score():
    features = {
        "source_count": 2,
        "total_transactions": 30,
        "verified_transaction_count": 20,
        "unclassified_transaction_count": 5,
        "corroborated_count": 10,
        "coverage_days": 120,
    }
    score_clean, _ = compute_evidence_score(features, conflict_count=0, raw_error_count=0)
    score_conflicted, _ = compute_evidence_score(features, conflict_count=2, raw_error_count=0)
    assert score_conflicted < score_clean


def test_grade_boundaries():
    assert determine_grade(92.0) == "A"
    assert determine_grade(85.0) == "A"
    assert determine_grade(75.0) == "B"
    assert determine_grade(70.0) == "B"
    assert determine_grade(60.0) == "C"
    assert determine_grade(45.0) == "D"


def test_insufficient_history_check():
    assert check_insufficient_history(coverage_days=30, active_months=1, valid_transaction_count=10) is True
    assert check_insufficient_history(coverage_days=180, active_months=6, valid_transaction_count=50) is False
