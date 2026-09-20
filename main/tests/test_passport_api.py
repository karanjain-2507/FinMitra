from fastapi.testclient import TestClient

from api_server import app


client = TestClient(app)


LOAN_GOAL = {
    "type": "LOAN_READINESS",
    "title": "Private vehicle goal",
    "target_amount": 100000,
    "deadline_months": 8,
    "annual_interest_rate": 0.14,
    "tenure_months": 24,
}


def test_issue_and_verify_passport_from_authoritative_assessment():
    assessment = client.get("/api/demo/strong")
    assessment_id = assessment.json()["assessment_id"]

    issued = client.post("/api/passports", json={"assessment_id": assessment_id})
    assert issued.status_code == 201
    credential = issued.json()
    assert credential["claims"]["credit_status"] == "ELIGIBLE_FOR_REVIEW"
    assert "borrower_id" not in credential
    assert "safe_emi" not in str(credential)

    verified = client.post(
        "/api/passports/verify",
        json={"credential_id": credential["credential_id"]},
    )
    assert verified.status_code == 200
    assert verified.json()["valid"] is True
    assert verified.json()["status"] == "VERIFIED"


def test_passport_goal_claim_is_recomputed_and_keeps_block():
    assessment = client.get("/api/demo/unpaid")
    issued = client.post(
        "/api/passports",
        json={
            "assessment_id": assessment.json()["assessment_id"],
            "goal": LOAN_GOAL,
        },
    )
    assert issued.status_code == 201
    body = issued.json()
    assert body["claims"]["credit_status"] == "BLOCKED"
    assert body["goal_claim"] == {
        "goal_type": "LOAN_READINESS",
        "outcome": "BLOCKED",
        "deadline_months": 8,
    }
    assert "Private vehicle goal" not in str(body)
    assert "100000" not in str(body)


def test_unknown_credential_is_a_safe_negative_result():
    response = client.post(
        "/api/passports/verify",
        json={"credential_id": "TP-IN-NOTFOUND"},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["status"] == "NOT_FOUND"


def test_passport_issue_rejects_client_claims():
    assessment = client.get("/api/demo/strong")
    response = client.post(
        "/api/passports",
        json={
            "assessment_id": assessment.json()["assessment_id"],
            "claims": {"credit_status": "ELIGIBLE_FOR_REVIEW"},
        },
    )
    assert response.status_code == 422
