#!/usr/bin/env python3
"""
run_profile.py — FinMitra Person 4 CLI

Assembles a complete FinMitra Credit Evidence Profile from a JSON input file.

Usage:
    python run_profile.py --input fixtures/strong_borrower.json
    python run_profile.py --input fixtures/unpaid_loan.json --pretty
    python run_profile.py --input fixtures/strong_borrower.json --output result.json
    python run_profile.py --input fixtures/strong_borrower.json --policy custom_policy.json

Options:
    --input  PATH   Path to the borrower input JSON file (required).
    --pretty        Pretty-print the JSON output with 2-space indentation.
    --output PATH   Write JSON output to a file instead of stdout.
    --policy PATH   Path to a custom CapacityPolicy JSON file.

Exit codes:
    0 — success
    1 — input/validation error
    2 — runtime error

Stdout: JSON output only (no debug logs).
Stderr: diagnostic messages, warnings, errors.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import NoReturn


# ---------------------------------------------------------------------------
# Stderr helper — all diagnostics go here, never to stdout
# ---------------------------------------------------------------------------

def _err(*args, **kwargs) -> None:  # noqa: D401
    """Print to stderr."""
    print(*args, file=sys.stderr, **kwargs)


def _die(message: str, code: int = 1) -> NoReturn:
    _err(f"\n[ERROR] {message}")
    sys.exit(code)


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------

def load_input(path: pathlib.Path) -> dict:
    """Load and parse the borrower input JSON file."""
    if not path.exists():
        _die(f"Input file not found: {path}")
    try:
        with path.open() as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        _die(f"Invalid JSON in {path}: {exc}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(input_data: dict, policy=None) -> dict:
    """
    Execute the full Person 4 pipeline:
      1. Parse CapacityInput from the 'capacity_input' key.
      2. Derive the scenario name for mock components.
      3. Run mock Evidence, Cashflow, Repayment engines.
      4. Run the Capacity Engine.
      5. Assemble the final profile.
      6. Return the profile as a serialisable dict.
    """
    # Import here so errors surface with useful messages
    from pydantic import ValidationError

    from capacity.engine import CapacityEngine
    from common.schemas import CapacityInput
    from fusion.profile_assembler import ProfileAssembler
    from mocks.cashflow import mock_cashflow
    from mocks.evidence import mock_evidence
    from mocks.repayment import mock_repayment

    # ------------------------------------------------------------------
    # Parse capacity input
    # ------------------------------------------------------------------
    raw_capacity_input = input_data.get("capacity_input")
    if raw_capacity_input is None:
        _die(
            "Input JSON must contain a 'capacity_input' key with capacity parameters."
        )

    try:
        capacity_input = CapacityInput.model_validate(raw_capacity_input)
    except ValidationError as exc:
        _die(f"CapacityInput validation failed:\n{exc}", code=1)

    # ------------------------------------------------------------------
    # Scenario for mock components (defaults to 'strong_borrower')
    # ------------------------------------------------------------------
    scenario = input_data.get("scenario", "strong_borrower")
    borrower_id = input_data.get("borrower_id")

    _err(f"[INFO] Scenario: {scenario}")
    _err(f"[INFO] Borrower ID: {borrower_id or '(not specified)'}")

    # ------------------------------------------------------------------
    # Mock component outputs
    # These simulate Person 1, 2, 3 outputs.
    # Replace with real engine calls when available.
    # ------------------------------------------------------------------
    _err("[INFO] Running mock Evidence Engine...")
    evidence = mock_evidence(scenario)

    _err("[INFO] Running mock Cash-Flow Model...")
    cashflow = mock_cashflow(scenario)

    _err("[INFO] Running mock Repayment Engine...")
    repayment = mock_repayment(scenario)

    new_credit_blocked = repayment.new_credit_blocked
    if new_credit_blocked:
        _err("[WARN] Repayment Engine: new_credit_blocked=True — safe EMI will be ₹0")

    # ------------------------------------------------------------------
    # Capacity Engine
    # ------------------------------------------------------------------
    _err("[INFO] Running Capacity Engine...")
    capacity_result = CapacityEngine.assess(
        inp=capacity_input,
        new_credit_blocked=new_credit_blocked,
        policy=policy,
    )
    _err(f"[INFO] Capacity status: {capacity_result.status}")
    _err(
        f"[INFO] Safe EMI: ₹{capacity_result.safe_emi.minimum:,.0f} – "
        f"₹{capacity_result.safe_emi.maximum:,.0f}"
    )

    # ------------------------------------------------------------------
    # Profile Assembler
    # ------------------------------------------------------------------
    _err("[INFO] Assembling FinMitra Credit Evidence Profile...")
    profile = ProfileAssembler.assemble(
        evidence=evidence,
        cashflow=cashflow,
        repayment=repayment,
        capacity=capacity_result,
        borrower_id=borrower_id,
    )
    _err(
        f"[INFO] Readiness index: "
        f"{profile.readiness_index if profile.readiness_index is not None else 'None (insufficient history)'}"
    )
    _err(f"[INFO] Overall confidence: {profile.overall_confidence:.2f}")

    return profile.model_dump(mode="json")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="run_profile",
        description="FinMitra Person 4 — Capacity Engine + Profile Assembler CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to borrower input JSON file.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=False,
        help="Pretty-print JSON output with 2-space indentation.",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Write JSON output to a file (default: stdout).",
    )
    parser.add_argument(
        "--policy",
        metavar="PATH",
        default=None,
        help="Path to a custom CapacityPolicy JSON file.",
    )

    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Load policy (optional)
    # ------------------------------------------------------------------
    policy = None
    if args.policy:
        from common.config import load_policy_from_file
        try:
            policy = load_policy_from_file(args.policy)
            _err(f"[INFO] Custom policy loaded from: {args.policy}")
        except FileNotFoundError as exc:
            _die(str(exc))
        except Exception as exc:
            _die(f"Failed to load policy: {exc}")

    # ------------------------------------------------------------------
    # Load input
    # ------------------------------------------------------------------
    input_path = pathlib.Path(args.input)
    input_data = load_input(input_path)

    # ------------------------------------------------------------------
    # Run pipeline
    # ------------------------------------------------------------------
    try:
        result = run_pipeline(input_data, policy=policy)
    except Exception as exc:
        _die(f"Pipeline error: {exc}", code=2)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    indent = 2 if args.pretty else None
    json_output = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.output:
        out_path = pathlib.Path(args.output)
        out_path.write_text(json_output, encoding="utf-8")
        _err(f"[INFO] Output written to: {out_path}")
    else:
        # Only JSON goes to stdout
        print(json_output)


if __name__ == "__main__":
    main()
