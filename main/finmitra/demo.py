"""Build reproducible hackathon demos from the bundled real fixtures."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


def build_demo(name: str) -> dict[str, Any]:
    if name == "thin":
        evidence = _load_evidence_fixture("thin_file")
        evidence.update(
            evaluation_date="2026-08-31",
            informal_loans=[],
            repayment_claims=[],
            capacity_context={
                "essential_household_expense": 7000,
                "available_balance_buffer": 1000,
            },
        )
        return evidence

    evidence = _load_evidence_fixture("strong_borrower")
    evidence["evaluation_date"] = "2026-08-31"
    evidence["sources"].append(_dense_qr_history())
    evidence["capacity_context"] = {
        "essential_household_expense": 10000,
        "available_balance_buffer": 15000,
        "existing_formal_emis": 0,
        "requested_loan_amount": 40000,
        "annual_interest_rate": 0.14,
        "tenure_months": 12,
    }
    evidence["informal_loans"] = []
    evidence["repayment_claims"] = []

    if name == "unpaid":
        repayment = _load_json(
            ROOT / "components" / "repayment" / "fixtures" / "unpaid_loan.json"
        )
        evidence["informal_loans"] = repayment["informal_loans"]
        evidence["repayment_claims"] = repayment["repayment_claims"]
    elif name != "strong":
        raise ValueError(f"unknown demo: {name}")
    return evidence


def _load_evidence_fixture(name: str) -> dict[str, Any]:
    path = (
        ROOT
        / "components"
        / "finmitra_person1"
        / "fixtures"
        / name
        / "input.json"
    )
    return copy.deepcopy(_load_json(path))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dense_qr_history() -> dict[str, Any]:
    records = []
    year, month = 2024, 9
    for sequence in range(24):
        for index in range(10):
            records.append(
                {
                    "transaction_id": f"DEMO-QR-{year}-{month:02d}-{index + 1:02d}",
                    "date": f"{year}-{month:02d}-{index + 2:02d}",
                    "amount": 5000 + (index * 150) + ((sequence % 6) * 50),
                    "direction": "CREDIT",
                    "narration": f"Merchant QR sale customer {index + 1}",
                    "counterparty": f"customer-{index + 1}@upi",
                    "mode": "UPI",
                    "status": "SUCCESS",
                    "is_qr": True,
                }
            )
        month += 1
        if month == 13:
            year += 1
            month = 1
    return {
        "source_id": "QR-DEMO-DENSE-01",
        "source_type": "QR",
        "metadata": {"purpose": "reproducible integration demo"},
        "records": records,
    }
