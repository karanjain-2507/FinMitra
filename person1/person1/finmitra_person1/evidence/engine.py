"""
Main Evidence Engine Orchestrator for FinMitra Person 1.
Coordinates Ingestion, Normalization, Deduplication, Anomaly Detection,
Validation, Corroboration, Grading, and Explainable Reason Generation.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import date

from ..enums import (
    EvidenceGrade,
    EvidenceStatus,
    ReasonDirection,
    TransactionCategory,
    VerificationLevel,
)
from ..schemas import (
    BorrowerInput,
    EvidenceResult,
    EvidenceBundle,
    Reason,
    NormalizedTransaction,
    ConflictRecord,
)
from ..config import (
    ENGINE_NAME,
    ENGINE_VERSION,
    STATUS_SUFFICIENT_MIN_SCORE,
    STATUS_DEGRADED_MIN_SCORE,
    REASON_CODES,
)
from ..ingestion import ingest_borrower
from ..normalization.normalize import normalize_records
from ..normalization.deduplication import run_deduplication
from .validation import validate_normalized_transactions
from .corroboration import compute_corroboration_metrics
from .anomaly import detect_anomalies
from .grading import compute_evidence_score, determine_grade, check_insufficient_history
from .confidence import compute_evidence_confidence


class EvidenceEngine:
    """Core evidence evaluation engine."""

    def __init__(self, version: str = ENGINE_VERSION) -> None:
        self.version = version

    def process(
        self,
        borrower: BorrowerInput,
        reference_date: Optional[date] = None,
        use_isolation_forest: bool = True
    ) -> EvidenceBundle:
        """
        Execute full end-to-end evidence pipeline for a borrower.
        """
        # Step 1: Ingestion
        raw_records = ingest_borrower(borrower)
        source_count = len(borrower.sources)

        # Step 2: Normalization
        normalized_txns, raw_errors = normalize_records(
            raw_records=raw_records,
            borrower_name=borrower.borrower_id,
            business_name=borrower.business_name
        )

        # Step 3: Validation
        valid_txns, validation_errors, val_conflicts = validate_normalized_transactions(
            transactions=normalized_txns,
            reference_date=reference_date
        )

        # Step 4: Multi-level Deduplication & Cross-Source Matching
        canonical_txns, dedup_conflicts, dedup_stats = run_deduplication(valid_txns)
        all_conflicts = val_conflicts + dedup_conflicts

        # Step 5: Anomaly Detection
        analyzed_txns, anomaly_count = detect_anomalies(
            transactions=canonical_txns,
            use_isolation_forest=use_isolation_forest
        )

        # Step 6: Corroboration & Features
        features = compute_corroboration_metrics(
            transactions=analyzed_txns,
            source_count=source_count
        )
        features["raw_transaction_count"] = len(raw_records)
        features["normalized_transaction_count"] = len(normalized_txns)
        features["valid_transaction_count"] = len(valid_txns)
        features["duplicate_transaction_count"] = (
            dedup_stats.get("exact_duplicates", 0) + dedup_stats.get("fingerprint_duplicates", 0)
        )
        features["cross_source_match_count"] = dedup_stats.get("cross_source_matches", 0)
        features["conflict_count"] = len(all_conflicts)
        features["anomaly_count"] = anomaly_count

        # Step 7: History Sufficiency Check
        insufficient_hist = check_insufficient_history(
            coverage_days=features["coverage_days"],
            active_months=features["active_months"],
            valid_transaction_count=features["valid_transaction_count"]
        )
        features["insufficient_history"] = insufficient_hist

        # Step 8: Evidence Quality Score & Grade
        total_raw_errors = len(raw_errors) + len(validation_errors)
        evidence_score, score_breakdown = compute_evidence_score(
            features=features,
            conflict_count=len(all_conflicts),
            raw_error_count=total_raw_errors
        )
        features["score_breakdown"] = score_breakdown
        grade = determine_grade(evidence_score)

        # Step 9: Evidence Confidence
        confidence = compute_evidence_confidence(
            features=features,
            evidence_score=evidence_score,
            insufficient_history=insufficient_hist,
            conflict_count=len(all_conflicts)
        )

        # Step 10: Evidence Status
        if insufficient_hist:
            status = "INSUFFICIENT"
        elif evidence_score >= STATUS_SUFFICIENT_MIN_SCORE:
            status = "SUFFICIENT"
        else:
            status = "DEGRADED"

        # Step 11: Explainable Reason Generation
        reasons, warnings = self._generate_reasons_and_warnings(
            features=features,
            raw_errors=raw_errors,
            validation_errors=validation_errors,
            conflicts=all_conflicts,
            dedup_stats=dedup_stats,
            anomaly_count=anomaly_count,
            insufficient_history=insufficient_hist,
            score=evidence_score,
            grade=grade
        )

        result = EvidenceResult(
            component="evidence",
            version=self.version,
            score=evidence_score,
            status=status,
            confidence=confidence,
            evidence_grade=grade,
            insufficient_history=insufficient_hist,
            features=features,
            reasons=reasons,
            warnings=warnings
        )

        source_summary = {
            "source_count": source_count,
            "sources": [
                {
                    "source_id": s.source_id,
                    "source_type": s.source_type.value,
                    "record_count": len(s.records)
                }
                for s in borrower.sources
            ],
            "raw_error_count": total_raw_errors
        }

        return EvidenceBundle(
            borrower_id=borrower.borrower_id,
            result=result,
            normalized_transactions=analyzed_txns,
            source_summary=source_summary,
            conflicts=all_conflicts
        )

    def _generate_reasons_and_warnings(
        self,
        features: Dict[str, Any],
        raw_errors: List[Dict[str, Any]],
        validation_errors: List[Dict[str, Any]],
        conflicts: List[ConflictRecord],
        dedup_stats: Dict[str, Any],
        anomaly_count: int,
        insufficient_history: bool,
        score: float,
        grade: str
    ) -> Tuple[List[Reason], List[str]]:
        """Construct structured, explainable EVxx reasons and warnings."""
        reasons: List[Reason] = []
        warnings: List[str] = []

        # EV01: Malformed records
        if raw_errors or validation_errors:
            cnt = len(raw_errors) + len(validation_errors)
            reasons.append(
                Reason(
                    code="EV01",
                    direction="NEGATIVE",
                    impact=-5.0,
                    message=f"{cnt} malformed or invalid transaction records were quarantined and excluded from normalized timeline."
                )
            )
            warnings.append(f"{cnt} raw records could not be parsed or validated.")

        # EV03: Duplicate records
        exact_dups = dedup_stats.get("exact_duplicates", 0)
        fp_dups = dedup_stats.get("fingerprint_duplicates", 0)
        if exact_dups > 0 or fp_dups > 0:
            reasons.append(
                Reason(
                    code="EV03",
                    direction="NEUTRAL",
                    impact=0.0,
                    message=f"{exact_dups + fp_dups} duplicate records identified and consolidated under canonical economic events."
                )
            )

        # EV04 / EV09: Cross-source duplicates & Corroboration
        cross_matches = dedup_stats.get("cross_source_matches", 0)
        if cross_matches > 0:
            reasons.append(
                Reason(
                    code="EV04",
                    direction="POSITIVE",
                    impact=10.0,
                    message=f"{cross_matches} cross-source transaction pairs matched (e.g. UPI collections matched with bank settlements)."
                )
            )

        # EV05: Conflicting records
        if conflicts:
            reasons.append(
                Reason(
                    code="EV05",
                    direction="NEGATIVE",
                    impact=-25.0 * len(conflicts),
                    message=f"{len(conflicts)} cross-source data conflicts detected (e.g. amount mismatch across records)."
                )
            )
            for c in conflicts:
                warnings.append(f"Conflict: {c.message}")

        # EV06: Unclassified transactions
        unclassified_cnt = features.get("unclassified_transaction_count", 0)
        if unclassified_cnt > 0:
            reasons.append(
                Reason(
                    code="EV06",
                    direction="NEUTRAL",
                    impact=-2.0,
                    message=f"{unclassified_cnt} transactions lack concrete merchant/document proof and remain UNCLASSIFIED."
                )
            )

        # EV07: Self-declared cash income
        self_decl_cnt = features.get("self_declared_transaction_count", 0)
        if self_decl_cnt > 0:
            reasons.append(
                Reason(
                    code="EV07",
                    direction="NEUTRAL",
                    impact=0.0,
                    message=f"{self_decl_cnt} self-declared cash income records preserved separately and excluded from predictive model eligibility."
                )
            )

        # EV08: Source connected
        if features.get("source_count", 0) > 0:
            reasons.append(
                Reason(
                    code="EV08",
                    direction="POSITIVE",
                    impact=5.0,
                    message=f"Financial data successfully ingested from {features.get('source_count', 1)} distinct data sources."
                )
            )

        # EV10: Document or ledger match
        verified_cnt = features.get("verified_transaction_count", 0)
        if verified_cnt > 0:
            reasons.append(
                Reason(
                    code="EV10",
                    direction="POSITIVE",
                    impact=15.0,
                    message=f"{verified_cnt} transactions verified against digital business ledgers, merchant QR registrations, or invoices."
                )
            )

        # EV11: Anomaly detected
        if anomaly_count > 0:
            reasons.append(
                Reason(
                    code="EV11",
                    direction="NEGATIVE",
                    impact=-4.0,
                    message=f"{anomaly_count} high-value or statistical anomaly transactions flagged for review (preserved in timeline)."
                )
            )
            warnings.append(f"{anomaly_count} transaction values are statistical outliers compared to standard activity.")

        # EV12: Insufficient history
        if insufficient_history:
            cov = features.get("coverage_days", 0)
            months = features.get("active_months", 0)
            txns = features.get("valid_transaction_count", 0)
            reasons.append(
                Reason(
                    code="EV12",
                    direction="NEGATIVE",
                    impact=-30.0,
                    message=f"Insufficient history: {cov} days, {months} active months, and {txns} transactions (minimum required: 90 days, 3 months, 30 transactions)."
                )
            )
            warnings.append("Borrower has thin/insufficient financial history.")

        # EV13: Low source coverage
        if features.get("source_count", 0) == 1 and features.get("corroboration_rate", 0) == 0:
            reasons.append(
                Reason(
                    code="EV13",
                    direction="NEGATIVE",
                    impact=-10.0,
                    message="Evidence is limited to a single uncorroborated data source."
                )
            )

        # EV16: High data completeness
        if len(raw_errors) == 0 and len(validation_errors) == 0 and features.get("total_transactions", 0) > 0:
            reasons.append(
                Reason(
                    code="EV16",
                    direction="POSITIVE",
                    impact=5.0,
                    message="100% of ingested records passed strict schema and chronological validation."
                )
            )

        # EV17: Multi-source corroboration strong
        if features.get("source_count", 0) >= 3 and features.get("corroboration_rate", 0) >= 0.50:
            reasons.append(
                Reason(
                    code="EV17",
                    direction="POSITIVE",
                    impact=10.0,
                    message="High multi-source corroboration provides strong evidence integrity."
                )
            )

        return reasons, warnings


# Module-level singleton helper instance
_DEFAULT_ENGINE = EvidenceEngine()


def assess(profile: BorrowerInput) -> EvidenceResult:
    """Public interface: Assess borrower evidence profile and return EvidenceResult."""
    bundle = _DEFAULT_ENGINE.process(profile)
    return bundle.result


def build_evidence_bundle(profile: BorrowerInput) -> EvidenceBundle:
    """Public interface: Build full EvidenceBundle including normalized transactions."""
    return _DEFAULT_ENGINE.process(profile)
