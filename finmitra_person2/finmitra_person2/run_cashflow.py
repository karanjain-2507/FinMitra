from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from model.inference import CashflowEngine
from schemas import BorrowerInput


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess business cash-flow health.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--artifact", type=Path, default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        profile = BorrowerInput.from_dict(raw)
        engine = CashflowEngine(args.artifact) if args.artifact else CashflowEngine()
        result = engine.assess(profile).to_dict()
        print(json.dumps(result, indent=2 if args.pretty else None, separators=None if args.pretty else (",", ":")))
        return 0
    except Exception as exc:
        print(f"cashflow assessment failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
