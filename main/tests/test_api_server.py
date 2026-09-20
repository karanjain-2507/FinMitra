import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api_server import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_demo_strong():
    res = client.get("/api/demo/strong")
    assert res.status_code == 200
    data = res.json()
    assert data["borrower_id"] == "BORR-KIRANA-001"
    assert "profile" in data
    assert data["profile"]["repayment"]["new_credit_blocked"] is False
    assert data["profile"]["evidence"]["evidence_grade"] in ("A", "B")


def test_demo_unpaid():
    res = client.get("/api/demo/unpaid")
    assert res.status_code == 200
    data = res.json()
    assert data["borrower_id"] == "BORR-KIRANA-001"
    assert data["profile"]["repayment"]["new_credit_blocked"] is True
    assert data["profile"]["safe_emi"]["maximum"] == 0.0


def test_demo_thin():
    res = client.get("/api/demo/thin")
    assert res.status_code == 200
    data = res.json()
    assert data["borrower_id"] == "BORR-THIN-003"
    assert data["profile"]["readiness_index"] is None


def test_csv_assess():
    csv_content = (
        "date,amount,direction,category,narration\n"
        "2026-01-10,5000,CREDIT,BUSINESS_INCOME,Customer UPI Payment\n"
        "2026-01-15,1200,DEBIT,OPERATING_EXPENSE,Wholesale Stock\n"
        "2026-02-10,6000,CREDIT,BUSINESS_INCOME,Direct QR Pay\n"
        "2026-02-20,1500,DEBIT,OPERATING_EXPENSE,Shop Rent\n"
        "2026-03-05,7500,CREDIT,BUSINESS_INCOME,Bulk Purchase\n"
    )
    files = {"file": ("statement.csv", csv_content, "text/csv")}
    data = {
        "borrower_id": "TEST-CSV-01",
        "business_name": "Test Store",
        "evaluation_date": "2026-03-10",
        "source_type": "BANK_STATEMENT",
        "household_expense": "2000",
        "balance_buffer": "1000",
    }
    res = client.post("/api/assess/csv", data=data, files=files)
    assert res.status_code == 200
    payload = res.json()
    assert payload["borrower_id"] == "TEST-CSV-01"
    assert "profile" in payload
