"""
Architectural Boundary Tests for Person 1.
Verifies that Person 1 maintains strict modular isolation:
- No imports of Person 2, 3, or 4 internals.
- Does not compute default probability, loan approval, repayment score, safe EMI, max principal, or readiness index.
"""
from __future__ import annotations
import sys
import inspect
from pathlib import Path
import pytest

import finmitra_person1
from finmitra_person1 import schemas, evidence, normalization, ingestion


FORBIDDEN_TERMS = [
    "predict_default",
    "calculate_safe_emi",
    "calculate_max_loan",
    "calculate_repayment_score",
    "credit_readiness_index",
    "approve_loan",
    "default_probability",
    "repayment_probability",
]


def test_no_forbidden_calculations_in_schemas():
    evidence_res_fields = schemas.EvidenceResult.model_fields.keys()
    for term in FORBIDDEN_TERMS:
        assert term not in evidence_res_fields, f"Forbidden field '{term}' found in EvidenceResult"


def test_no_person_2_3_4_imports():
    # Check all loaded modules under finmitra_person1
    for mod_name, mod in sys.modules.items():
        if mod_name.startswith("finmitra_person1"):
            source = inspect.getsource(mod) if hasattr(mod, "__file__") and mod.__file__ else ""
            assert "person2" not in source.lower(), f"Forbidden reference to person2 in {mod_name}"
            assert "person3" not in source.lower(), f"Forbidden reference to person3 in {mod_name}"
            assert "person4" not in source.lower(), f"Forbidden reference to person4 in {mod_name}"
