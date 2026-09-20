import json
from pathlib import Path

import pytest

from config import ROOT
from schemas import BorrowerInput


@pytest.fixture
def stable_profile() -> BorrowerInput:
    raw = json.loads((ROOT / "fixtures" / "stable_kirana" / "input.json").read_text(encoding="utf-8"))
    return BorrowerInput.from_dict(raw)


@pytest.fixture
def thin_profile() -> BorrowerInput:
    raw = json.loads((ROOT / "fixtures" / "thin_file" / "input.json").read_text(encoding="utf-8"))
    return BorrowerInput.from_dict(raw)
