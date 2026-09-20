"""Orchestration for the real four-component FinMitra pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .adapters import (
    capacity_payload,
    cashflow_payload,
    evidence_payload,
    repayment_payload,
)
from .schemas import IntegratedBorrowerInput


ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = ROOT / "components"
PIPELINE_VERSION = "1.0.0"


class AssessmentError(RuntimeError):
    """Raised when a component fails or violates the JSON boundary."""


def _run_component(
    name: str,
    script: Path,
    payload: dict[str, Any],
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False)
            temp_path = Path(handle.name)
        command = [sys.executable, str(script), "--input", str(temp_path)]
        command.extend(extra_args or [])
        completed = subprocess.run(
            command,
            cwd=script.parent,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise AssessmentError(f"{name} failed: {detail}")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AssessmentError(f"{name} returned invalid JSON") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def assess(
    profile: IntegratedBorrowerInput,
    *,
    include_transactions: bool = False,
) -> dict[str, Any]:
    """Run all four real engines and return one auditable result."""

    evidence_bundle = _run_component(
        "evidence engine",
        COMPONENTS / "finmitra_person1" / "run_evidence.py",
        evidence_payload(profile),
        ["--reference-date", profile.evaluation_date.isoformat()],
    )
    cashflow_input = cashflow_payload(profile, evidence_bundle)
    cashflow = _run_component(
        "cash-flow engine",
        COMPONENTS / "cashflow" / "run_cashflow.py",
        cashflow_input,
    )
    repayment_input = repayment_payload(profile, evidence_bundle, cashflow)
    repayment = _run_component(
        "repayment engine",
        COMPONENTS / "repayment" / "run_repayment.py",
        repayment_input,
    )
    capacity_input = capacity_payload(profile, evidence_bundle, cashflow, repayment)
    final_profile = _run_component(
        "capacity and profile engine",
        COMPONENTS / "profile" / "run_integrated_profile.py",
        {
            "borrower_id": profile.borrower_id,
            "evidence": evidence_bundle["result"],
            "cashflow": cashflow,
            "repayment": repayment,
            "capacity_input": capacity_input,
        },
    )

    result: dict[str, Any] = {
        "pipeline_version": PIPELINE_VERSION,
        "borrower_id": profile.borrower_id,
        "evaluation_date": profile.evaluation_date.isoformat(),
        "profile": final_profile,
        "lineage": {
            "source_count": evidence_bundle["source_summary"].get("source_count", 0),
            "raw_transaction_count": evidence_bundle["result"]["features"].get(
                "raw_transaction_count", 0
            ),
            "normalized_transaction_count": len(
                evidence_bundle["normalized_transactions"]
            ),
            "cashflow_transaction_count": len(cashflow_input["transactions"]),
            "repayment_claim_count": len(profile.repayment_claims),
            "informal_loan_count": len(profile.informal_loans),
        },
    }
    if include_transactions:
        result["normalized_transactions"] = evidence_bundle["normalized_transactions"]
    return result
