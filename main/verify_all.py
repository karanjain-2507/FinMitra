#!/usr/bin/env python3
"""Run the integration suite and every preserved component suite in isolation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SUITES = (
    ("integration", ROOT),
    ("evidence", ROOT / "components" / "finmitra_person1"),
    ("cashflow", ROOT / "components" / "cashflow"),
    ("repayment", ROOT / "components" / "repayment"),
    ("capacity/profile", ROOT / "components" / "profile"),
)


def main() -> int:
    failures = []
    for name, directory in SUITES:
        print(f"\n=== {name} ===", flush=True)
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"], cwd=directory, check=False
        )
        if completed.returncode:
            failures.append(name)
    if failures:
        print(f"\nFailed suites: {', '.join(failures)}", file=sys.stderr)
        return 1
    print("\nAll FinMitra suites passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
