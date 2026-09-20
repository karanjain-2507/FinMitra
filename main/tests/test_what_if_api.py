from fastapi.testclient import TestClient
import json

from api_server import app


client = TestClient(app)


LOAN_GOAL = {
    "type": "LOAN_READINESS",
    "title": "Car",
    "target_amount": 100000,
    "deadline_months": 8,
    "annual_interest_rate": 0.14,
    "tenure_months": 24,
    "desired_buffer": None,
}


def test_demo_what_if_returns_structured_plan():
    response = client.post("/api/what-if/demo/strong", json=LOAN_GOAL)
    assert response.status_code == 200
    plan = response.json()
    assert plan["schema_version"] == "1.0"
    assert plan["goal"]["type"] == "LOAN_READINESS"
    assert plan["required_state"]["required_emi"] == 4801.29
    assert plan["outcome"] in {"ACHIEVABLE_NOW", "ACHIEVABLE_WITH_CHANGES"}


def test_unknown_demo_is_rejected():
    response = client.post("/api/what-if/demo/not-real", json=LOAN_GOAL)
    assert response.status_code == 400


def test_incomplete_loan_goal_is_rejected():
    invalid = dict(LOAN_GOAL)
    invalid.pop("tenure_months")
    response = client.post("/api/what-if/demo/strong", json=invalid)
    assert response.status_code == 422


def test_interest_rate_must_be_decimal_not_percentage_points():
    invalid = {**LOAN_GOAL, "annual_interest_rate": 14}
    response = client.post("/api/what-if/demo/strong", json=invalid)
    assert response.status_code == 422


def test_csv_what_if_reassesses_the_source_statement():
    csv_content = (
        "date,amount,direction,category,narration\n"
        "2026-01-10,5000,CREDIT,BUSINESS_INCOME,Customer Payment\n"
        "2026-01-15,1200,DEBIT,OPERATING_EXPENSE,Stock\n"
        "2026-02-10,6000,CREDIT,BUSINESS_INCOME,QR Pay\n"
        "2026-02-20,1500,DEBIT,OPERATING_EXPENSE,Rent\n"
        "2026-03-05,7500,CREDIT,BUSINESS_INCOME,Bulk Purchase\n"
    )
    response = client.post(
        "/api/what-if/csv",
        files={"file": ("statement.csv", csv_content, "text/csv")},
        data={
            "goal": json.dumps(LOAN_GOAL),
            "borrower_id": "WHAT-IF-CSV",
            "evaluation_date": "2026-03-10",
            "household_expense": "2000",
            "balance_buffer": "1000",
        },
    )
    assert response.status_code == 200
    assert response.json()["outcome"] == "INSUFFICIENT_DATA"
    assert response.json()["current_state"]["monthly_inflow"] is None
    assert response.json()["gap"]["monthly_cashflow_gap"] is None


def test_primary_what_if_uses_server_owned_assessment():
    assessment = client.get("/api/demo/unpaid")
    assert assessment.status_code == 200
    assessment_id = assessment.json()["assessment_id"]

    response = client.post(
        "/api/what-if",
        json={"assessment_id": assessment_id, "goal": LOAN_GOAL},
    )
    assert response.status_code == 200
    assert response.json()["outcome"] == "BLOCKED"


def test_primary_what_if_rejects_client_supplied_assessment_input():
    response = client.post(
        "/api/what-if",
        json={"assessment_input": {}, "goal": LOAN_GOAL},
    )
    assert response.status_code == 422


def test_unknown_assessment_id_is_rejected():
    response = client.post(
        "/api/what-if",
        json={"assessment_id": "not-a-real-assessment", "goal": LOAN_GOAL},
    )
    assert response.status_code == 404


def test_goal_amount_requires_cents_and_realistic_bound():
    too_precise = {**LOAN_GOAL, "target_amount": 100000.001}
    too_large = {**LOAN_GOAL, "target_amount": 100000000.01}
    tiny = {**LOAN_GOAL, "target_amount": 1e-20}
    astronomical = {**LOAN_GOAL, "target_amount": 1e300}
    assert client.post("/api/what-if/demo/strong", json=too_precise).status_code == 422
    assert client.post("/api/what-if/demo/strong", json=too_large).status_code == 422
    assert client.post("/api/what-if/demo/strong", json=tiny).status_code == 422
    assert client.post("/api/what-if/demo/strong", json=astronomical).status_code == 422


def test_request_size_limit():
    response = client.post(
        "/api/assess",
        content=b"x" * (2 * 1024 * 1024 + 1),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
