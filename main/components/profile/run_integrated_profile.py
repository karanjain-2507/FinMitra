#!/usr/bin/env python3
"""Run Person 4 against real upstream component outputs, never mocks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from capacity.engine import CapacityEngine
from common.schemas import (
    CapacityInput,
    CashflowResult,
    EvidenceResult,
    RepaymentResult,
)
from fusion.profile_assembler import ProfileAssembler


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble a profile from real engine outputs")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        evidence = EvidenceResult.model_validate(payload["evidence"])
        cashflow = CashflowResult.model_validate(payload["cashflow"])
        repayment = RepaymentResult.model_validate(payload["repayment"])
        capacity_input = CapacityInput.model_validate(payload["capacity_input"])
        capacity = CapacityEngine.assess(
            inp=capacity_input,
            new_credit_blocked=repayment.new_credit_blocked,
        )
        profile = ProfileAssembler.assemble(
            evidence=evidence,
            cashflow=cashflow,
            repayment=repayment,
            capacity=capacity,
            borrower_id=payload.get("borrower_id"),
        )
        print(json.dumps(profile.model_dump(mode="json"), indent=2 if args.pretty else None))
        return 0
    except Exception as exc:
        print(f"integrated profile assembly failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
