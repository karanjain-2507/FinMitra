"""CLI for the deterministic repayment engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.schemas import BorrowerInput
from repayment.engine import assess


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FinMitra repayment engine")
    parser.add_argument("--input", required=True, help="Path to a BorrowerInput JSON file")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text())
    result = assess(BorrowerInput.model_validate(payload))
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
