"""Issue and verify signed, selectively disclosed FinMitra credentials."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any

from .schemas import (
    FinancialPassport,
    PassportClaims,
    PassportGoalClaim,
    PassportProof,
    PassportVerification,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PassportService:
    """Process-local credential issuer using a configurable HMAC signing key."""

    def __init__(self, signing_key: bytes | None = None, *, validity_days: int = 30) -> None:
        configured = os.environ.get("FINMITRA_PASSPORT_SIGNING_KEY")
        self._key = signing_key or (configured.encode("utf-8") if configured else secrets.token_bytes(32))
        self.validity_days = validity_days
        self.key_id = hashlib.sha256(self._key).hexdigest()[:12]
        self._credentials: dict[str, FinancialPassport] = {}
        self._lock = RLock()

    def _signature(self, unsigned: dict[str, Any]) -> str:
        canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hmac.new(self._key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def _subject_id(self, borrower_id: str) -> str:
        digest = hmac.new(self._key, borrower_id.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"FM-{digest[:16].upper()}"

    @staticmethod
    def _claims(assessment: dict[str, Any]) -> PassportClaims:
        profile = assessment["profile"]
        evidence = profile["evidence"]
        cashflow = profile["cashflow"]
        repayment = profile["repayment"]
        capacity = profile["capacity"]
        readiness = profile.get("readiness_index")
        confidence = float(profile.get("overall_confidence") or 0)
        insufficient = bool(evidence.get("insufficient_history")) or cashflow.get("status") == "INSUFFICIENT_DATA"
        blocked = bool(repayment.get("new_credit_blocked"))
        if blocked:
            credit_status = "BLOCKED"
        elif insufficient:
            credit_status = "INSUFFICIENT_DATA"
        else:
            credit_status = "ELIGIBLE_FOR_REVIEW"
        if readiness is None:
            readiness_band = "UNAVAILABLE"
        elif readiness >= 75:
            readiness_band = "STRONG"
        elif readiness >= 50:
            readiness_band = "MODERATE"
        else:
            readiness_band = "DEVELOPING"
        confidence_band = "HIGH" if confidence >= 0.8 else "MEDIUM" if confidence >= 0.6 else "LOW"
        stress_tests = capacity.get("stress_tests", [])
        grade = str(evidence.get("evidence_grade") or "UNKNOWN")
        if grade not in {"A", "B", "C", "D", "INSUFFICIENT"}:
            grade = "UNKNOWN"
        return PassportClaims(
            evidence_grade=grade,
            cashflow_status=str(cashflow.get("status", "UNKNOWN")),
            repayment_status=str(repayment.get("status", "UNKNOWN")),
            credit_status=credit_status,
            readiness_band=readiness_band,
            confidence_band=confidence_band,
            stress_checks_passed=sum(bool(item.get("passed")) for item in stress_tests),
            stress_checks_total=len(stress_tests),
        )

    def issue(
        self,
        assessment: dict[str, Any],
        *,
        goal_claim: PassportGoalClaim | None = None,
    ) -> FinancialPassport:
        issued_at = _utc_now()
        credential_id = f"TP-IN-{secrets.token_hex(4).upper()}"
        unsigned = {
            "schema_version": "1.0",
            "credential_id": credential_id,
            "issuer": "FinMitra",
            "subject_id": self._subject_id(str(assessment["borrower_id"])),
            "issued_at": _iso(issued_at),
            "expires_at": _iso(issued_at + timedelta(days=self.validity_days)),
            "assessment_date": str(assessment["evaluation_date"]),
            "claims": self._claims(assessment).model_dump(mode="json"),
            "goal_claim": goal_claim.model_dump(mode="json") if goal_claim else None,
        }
        credential = FinancialPassport(
            **unsigned,
            proof=PassportProof(key_id=self.key_id, signature=self._signature(unsigned)),
        )
        with self._lock:
            self._credentials[credential_id] = copy.deepcopy(credential)
        return credential

    def verify(self, credential_id: str) -> PassportVerification:
        now = _utc_now()
        with self._lock:
            credential = copy.deepcopy(self._credentials.get(credential_id.upper()))
        if credential is None:
            return PassportVerification(
                credential_id=credential_id,
                valid=False,
                status="NOT_FOUND",
                verified_at=_iso(now),
            )
        payload = credential.model_dump(mode="json", exclude={"proof"})
        signature_valid = hmac.compare_digest(
            credential.proof.signature,
            self._signature(payload),
        ) and credential.proof.key_id == self.key_id
        expires = datetime.fromisoformat(credential.expires_at.replace("Z", "+00:00"))
        status = "INVALID" if not signature_valid else "EXPIRED" if expires <= now else "VERIFIED"
        return PassportVerification(
            credential_id=credential.credential_id,
            valid=status == "VERIFIED",
            status=status,
            verified_at=_iso(now),
            issuer=credential.issuer,
            subject_id=credential.subject_id,
            expires_at=credential.expires_at,
            claims=credential.claims if signature_valid else None,
            goal_claim=credential.goal_claim if signature_valid else None,
        )

    def get(self, credential_id: str) -> FinancialPassport | None:
        with self._lock:
            credential = self._credentials.get(credential_id.upper())
            return copy.deepcopy(credential) if credential else None


passport_service = PassportService()
