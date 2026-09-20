#!/usr/bin/env python3
"""Command-line entry point for the integrated FinMitra pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from finmitra.demo import build_demo
from finmitra.runner import AssessmentError, assess
from finmitra.schemas import IntegratedBorrowerInput


def _configure_utf8_console() -> None:
    """Prevent Unicode assessment text from crashing Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def _money(value: float | int | None) -> str:
    return "Unknown" if value is None else f"₹{float(value):,.0f}"


def render_summary(result: dict[str, Any]) -> str:
    """Render the integrated result as a short hackathon-friendly report."""
    profile = result["profile"]
    evidence = profile["evidence"]
    cashflow = profile["cashflow"]
    repayment = profile["repayment"]
    safe_emi = profile["safe_emi"]

    stress = cashflow.get("stress_probability")
    stress_text = (
        "Unknown (insufficient history)" if stress is None else f"{stress:.1%}"
    )
    readiness = profile.get("readiness_index")
    readiness_text = "Unknown" if readiness is None else f"{readiness:.1f}/100"
    blocked = bool(repayment.get("new_credit_blocked"))
    if blocked:
        outcome = "BLOCKED — unresolved repayment obligation"
    elif stress is None:
        outcome = "INSUFFICIENT DATA — collect more verified history"
    else:
        outcome = "READY FOR LENDER REVIEW"

    findings: list[tuple[int, str]] = []
    for component in (repayment, cashflow, profile["capacity"], evidence):
        for reason in component.get("reasons", []):
            message = reason.get("message")
            if not message:
                continue
            direction = reason.get("direction")
            priority = 0 if direction == "NEGATIVE" else 1 if direction == "POSITIVE" else 2
            findings.append((priority, message))
    unique_findings: list[str] = []
    for _, message in sorted(findings, key=lambda item: item[0]):
        if message not in unique_findings:
            unique_findings.append(message)
        if len(unique_findings) == 4:
            break

    lines = [
        "",
        "=" * 58,
        "FINMITRA ASSESSMENT",
        "=" * 58,
        f"Borrower:             {result['borrower_id']}",
        f"Evidence grade:       {evidence.get('evidence_grade', 'Unknown')}",
        f"Cash-flow stress:     {stress_text}",
        f"Cash-flow health:     {cashflow.get('score') if cashflow.get('score') is not None else 'Unknown'}",
        f"Repayment status:     {repayment.get('status', 'Unknown')}",
        f"Credit blocked:       {'YES' if blocked else 'No'}",
        f"Readiness:            {readiness_text}",
        f"Safe EMI:             {_money(safe_emi.get('minimum'))} – {_money(safe_emi.get('maximum'))}",
        "-" * 58,
        f"Outcome: {outcome}",
    ]
    if unique_findings:
        lines.extend(("", "Main findings:"))
        lines.extend(f"  - {message}" for message in unique_findings)
    lines.append("=" * 58)
    return "\n".join(lines)


def _read_number(prompt: str, default: float = 0.0) -> float:
    raw = input(f"{prompt} [{default:g}]: ").strip()
    return default if not raw else float(raw.replace(",", ""))


def _latest_csv_date(rows: list[dict[str, str]]) -> str:
    candidates: list[date] = []
    for row in rows:
        lowered = {str(key).strip().lower(): value for key, value in row.items()}
        raw = next(
            (
                lowered.get(key)
                for key in ("date", "txn date", "transaction date", "value date")
                if lowered.get(key)
            ),
            None,
        )
        if not raw:
            continue
        for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                candidates.append(datetime.strptime(str(raw).strip(), pattern).date())
                break
            except ValueError:
                pass
    return max(candidates, default=date.today()).isoformat()


def _build_csv_input() -> dict[str, Any]:
    csv_path = Path(input("CSV path: ").strip().strip('"')).expanduser()
    if not csv_path.is_file():
        raise ValueError(f"CSV file not found: {csv_path}")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("CSV contains no transaction rows")

    borrower_id = input("Borrower ID [BORROWER-001]: ").strip() or "BORROWER-001"
    business_name = input("Business name [Not provided]: ").strip() or None
    inferred_date = _latest_csv_date(rows)
    evaluation_date = input(f"Evaluation date [{inferred_date}]: ").strip() or inferred_date
    source_type = (
        input("Source type [BANK_STATEMENT]: ").strip().upper()
        or "BANK_STATEMENT"
    )
    household_expense = _read_number("Monthly household expense", 0)
    balance_buffer = _read_number("Available balance buffer", 0)
    return {
        "borrower_id": borrower_id,
        "business_name": business_name,
        "evaluation_date": evaluation_date,
        "sources": [
            {
                "source_id": f"CLI-{source_type}-01",
                "source_type": source_type,
                "records": rows,
                "metadata": {"filename": csv_path.name, "entered_via": "interactive_cli"},
            }
        ],
        "informal_loans": [],
        "repayment_claims": [],
        "capacity_context": {
            "essential_household_expense": household_expense,
            "available_balance_buffer": balance_buffer,
        },
    }


def _interactive_input() -> dict[str, Any] | None:
    print("\nFINMITRA — Alternative Credit Assessment")
    print("1. Strong shopkeeper demo")
    print("2. Unpaid informal-loan demo")
    print("3. Thin-history demo")
    print("4. Assess a transaction CSV")
    print("5. Assess a complete borrower JSON")
    print("0. Exit")
    choice = input("\nChoose an option: ").strip()
    demos = {"1": "strong", "2": "unpaid", "3": "thin"}
    if choice in demos:
        return build_demo(demos[choice])
    if choice == "4":
        return _build_csv_input()
    if choice == "5":
        path = Path(input("JSON path: ").strip().strip('"')).expanduser()
        return json.loads(path.read_text(encoding="utf-8"))
    if choice == "0":
        return None
    raise ValueError("Choose one of the displayed options")


def main() -> int:
    _configure_utf8_console()
    parser = argparse.ArgumentParser(description="Run all four FinMitra engines")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="Integrated borrower JSON")
    source.add_argument(
        "--demo", choices=("strong", "unpaid", "thin"), help="Bundled demo scenario"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--include-transactions", action="store_true")
    args = parser.parse_args()

    try:
        if args.demo:
            raw = build_demo(args.demo)
        elif args.input:
            raw = json.loads(args.input.read_text(encoding="utf-8"))
        else:
            raw = _interactive_input()
            if raw is None:
                return 0
        profile = IntegratedBorrowerInput.model_validate(raw)
        result = assess(profile, include_transactions=args.include_transactions)
        if not args.demo and not args.input:
            print(render_summary(result))
            return 0
        rendered = json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
            print(f"Wrote {args.output}", file=sys.stderr)
        else:
            print(rendered)
        return 0
    except (OSError, json.JSONDecodeError, ValidationError, AssessmentError, ValueError) as exc:
        print(f"FinMitra assessment failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
