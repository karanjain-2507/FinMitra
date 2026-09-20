from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import pytest

from finmitra.what_if.calculations import (
    compute_emi,
    compute_max_principal,
    first_affordable_tenure,
)


def test_zero_interest_emi_and_inverse():
    emi = compute_emi(Decimal("100000"), Decimal("0"), 10)
    assert emi == Decimal("10000.00")
    assert compute_max_principal(emi, Decimal("0"), 10) == Decimal("100000.00")


def test_standard_emi_matches_capacity_fixture():
    # The integrated strong demo's capacity engine returns ₹3,591.48.
    assert compute_emi(Decimal("40000"), Decimal("0.14"), 12) == Decimal("3591.48")


def test_first_affordable_tenure_returns_shortest_month_count():
    tenure = first_affordable_tenure(
        Decimal("100000"), Decimal("0.14"), Decimal("5000"), 12
    )
    assert tenure is not None
    assert compute_emi(Decimal("100000"), Decimal("0.14"), tenure) <= Decimal("5000")
    assert compute_emi(Decimal("100000"), Decimal("0.14"), tenure - 1) > Decimal("5000")


@pytest.mark.parametrize(
    "principal,rate,months",
    [(Decimal("0"), Decimal("0.1"), 12), (Decimal("1"), Decimal("-0.1"), 12), (Decimal("1"), Decimal("0.1"), 0)],
)
def test_invalid_emi_inputs_are_rejected(principal, rate, months):
    with pytest.raises(ValueError):
        compute_emi(principal, rate, months)


def test_emi_matches_authoritative_capacity_component_across_supported_domain():
    cases = [
        ("0.01", "0", 1),
        ("100000", "0.14", 24),
        ("999999.99", "0.000001", 359),
        ("100000000.00", "1", 360),
    ]
    profile_dir = Path(__file__).resolve().parents[1] / "components" / "profile"
    script = (
        "import json; from capacity.calculations import compute_emi; "
        f"cases={json.dumps(cases)}; "
        "print(json.dumps([compute_emi(float(p),float(r),n) for p,r,n in cases]))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=profile_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    authoritative = json.loads(completed.stdout)

    for (principal, rate, months), expected in zip(cases, authoritative, strict=True):
        actual = compute_emi(Decimal(principal), Decimal(rate), months)
        assert abs(actual - Decimal(str(expected))) <= Decimal("0.01")
