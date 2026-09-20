#!/usr/bin/env python3
"""
FinMitra Person 1: Evidence Engine CLI Runner.
Executes data ingestion, normalization, and evidence evaluation from JSON files.
Writes standardized EvidenceBundle JSON strictly to stdout.
All logging and human-readable diagnostic messages are directed to stderr.
"""
from __future__ import annotations
import sys
import os
import json
import argparse
from datetime import date
from pathlib import Path

# Ensure package directory is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

try:
    from finmitra_person1.schemas import BorrowerInput
    from finmitra_person1.evidence.engine import EvidenceEngine
    from finmitra_person1.config import ENGINE_VERSION
except ImportError:
    # Direct import fallback if executed from within package directory
    from schemas import BorrowerInput
    from evidence.engine import EvidenceEngine
    from config import ENGINE_VERSION


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FinMitra Evidence Engine CLI (Person 1: Ingestion + Normalization + Evidence)"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Path to input Borrower JSON file"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Optional path to write output EvidenceBundle JSON"
    )
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="Pretty-print the stdout JSON with 2-space indentation"
    )
    parser.add_argument(
        "--reference-date",
        type=date.fromisoformat,
        default=None,
        help="Deterministic assessment cutoff in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"FinMitra Evidence Engine v{ENGINE_VERSION}"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.stderr.write(f"ERROR: Input file not found: {input_path}\n")
        return 1

    try:
        sys.stderr.write(f"[*] Reading input payload from: {input_path}\n")
        with open(input_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        borrower = BorrowerInput.model_validate(raw_data)
        sys.stderr.write(f"[*] Successfully parsed BorrowerInput for ID: {borrower.borrower_id}\n")

        engine = EvidenceEngine()
        sys.stderr.write("[*] Processing ingestion, normalization, and evidence evaluation...\n")
        bundle = engine.process(borrower, reference_date=args.reference_date)

        # Serialize EvidenceBundle
        # Use Pydantic's mode='json' to ensure dates and enums serialize cleanly
        bundle_dict = bundle.model_dump(mode="json")
        indent = 2 if args.pretty else None
        output_json = json.dumps(bundle_dict, indent=indent, default=str)

        # Output to file if specified
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as out_f:
                out_f.write(output_json + "\n")
            sys.stderr.write(f"[*] Output written to: {out_path}\n")

        # Always write JSON strictly to stdout
        sys.stdout.write(output_json + "\n")
        sys.stdout.flush()

        res = bundle.result
        sys.stderr.write(
            f"[*] Completed! Score: {res.score} | Grade: {res.evidence_grade} | "
            f"Status: {res.status} | Confidence: {res.confidence} | "
            f"Normalized Txns: {len(bundle.normalized_transactions)}\n"
        )
        return 0

    except Exception as e:
        sys.stderr.write(f"ERROR: Failed during evidence processing: {str(e)}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
