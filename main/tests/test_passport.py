from finmitra.passport.service import PassportService


def assessment(*, blocked=False, insufficient=False):
    return {
        "borrower_id": "PRIVATE-BORROWER-123",
        "evaluation_date": "2026-09-20",
        "profile": {
            "overall_confidence": 0.86,
            "readiness_index": 82.5 if not insufficient else None,
            "evidence": {
                "evidence_grade": "A" if not insufficient else "D",
                "insufficient_history": insufficient,
            },
            "cashflow": {"status": "INSUFFICIENT_DATA" if insufficient else "SUFFICIENT"},
            "repayment": {
                "status": "SEVERELY_UNPAID" if blocked else "CURRENT",
                "new_credit_blocked": blocked,
            },
            "capacity": {
                "stress_tests": [
                    {"name": "income_drop", "passed": True},
                    {"name": "zero_income", "passed": False},
                ]
            },
        },
    }


def test_passport_is_signed_pseudonymous_and_selectively_disclosed():
    service = PassportService(b"test-signing-key")
    credential = service.issue(assessment())
    verification = service.verify(credential.credential_id)
    serialized = credential.model_dump(mode="json")

    assert verification.valid is True
    assert verification.status == "VERIFIED"
    assert credential.subject_id.startswith("FM-")
    assert credential.claims.credit_status == "ELIGIBLE_FOR_REVIEW"
    assert credential.claims.stress_checks_passed == 1
    assert "PRIVATE-BORROWER-123" not in str(serialized)
    assert "monthly_inflow" not in str(serialized)
    assert "safe_emi" not in str(serialized)


def test_passport_preserves_repayment_block_and_insufficient_data():
    service = PassportService(b"test-signing-key")
    blocked = service.issue(assessment(blocked=True))
    thin = service.issue(assessment(insufficient=True))

    assert blocked.claims.credit_status == "BLOCKED"
    assert thin.claims.credit_status == "INSUFFICIENT_DATA"
    assert thin.claims.readiness_band == "UNAVAILABLE"


def test_tampered_stored_credential_fails_signature_verification():
    service = PassportService(b"test-signing-key")
    credential = service.issue(assessment())
    service._credentials[credential.credential_id].claims.credit_status = "BLOCKED"

    verification = service.verify(credential.credential_id)
    assert verification.valid is False
    assert verification.status == "INVALID"
    assert verification.claims is None


def test_expired_credential_is_rejected():
    service = PassportService(b"test-signing-key", validity_days=-1)
    credential = service.issue(assessment())
    verification = service.verify(credential.credential_id)
    assert verification.valid is False
    assert verification.status == "EXPIRED"
