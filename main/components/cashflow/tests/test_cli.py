import json
import subprocess
import sys

from config import ROOT


def test_cli_stdout_is_valid_json():
    result = subprocess.run(
        [sys.executable, "run_cashflow.py", "--input", "fixtures/stable_kirana/input.json"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["component"] == "cashflow"
    assert result.stderr == ""


def test_invalid_cli_input_fails_cleanly(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "run_cashflow.py", "--input", str(path)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "failed" in result.stderr
