"""
End-to-end integration and CLI execution tests.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import pytest

from finmitra_person1.schemas import BorrowerInput
from finmitra_person1.evidence.engine import assess, build_evidence_bundle

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = PROJECT_ROOT / "fixtures" / "strong_borrower" / "input.json"


def test_public_engine_interfaces():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    borrower = BorrowerInput.model_validate(data)

    # Test assess()
    result = assess(borrower)
    assert result.component == "evidence"
    assert result.score is not None
    assert result.evidence_grade in ("A", "B", "C", "D")

    # Test build_evidence_bundle()
    bundle = build_evidence_bundle(borrower)
    assert bundle.borrower_id == borrower.borrower_id
    assert len(bundle.normalized_transactions) > 0


def test_cli_execution_clean_stdout():
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "run_evidence.py"),
        "--input",
        str(FIXTURE_PATH)
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0
    # Stderr has diagnostic logs
    assert "Completed!" in proc.stderr
    # Stdout is strictly valid JSON
    output_dict = json.loads(proc.stdout)
    assert "borrower_id" in output_dict
    assert "result" in output_dict
    assert output_dict["result"]["component"] == "evidence"


def test_cli_missing_input_exits_with_error():
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "run_evidence.py"),
        "--input",
        "non_existent_file.json"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 1
    assert "ERROR: Input file not found" in proc.stderr
