"""
Adversarial Test Suite for FinMitra Person 1 (Evidence Engine).
Tests malformed inputs, edge cases, financial invariants, deduplication attacks,
categorization attacks, grade boundaries, pipeline resilience, and determinism.
"""
import copy
import json
import pytest
from datetime import date, timedelta
from pathlib import Path
from pydantic import ValidationError

from finmitra_person1.enums import (
    TransactionCategory,
    TransactionMode,
    DataSourceType,
    VerificationLevel,
    CategorySource,
    EvidenceGrade,
    EvidenceStatus,
    ConflictType,
)
from finmitra_person1.schemas import (
    NormalizedTransaction,
    ProvenanceRecord,
    SourceInput,
    BorrowerInput,
    EvidenceResult,
    EvidenceBundle,
)
from finmitra_person1.ingestion import ingest_borrower
from finmitra_person1.ingestion.base import parse_amount_to_paise, parse_flexible_date
from finmitra_person1.normalization.normalize import normalize_record, normalize_records
from finmitra_person1.normalization.categorization import classify_transaction
from finmitra_person1.normalization.deduplication import run_deduplication
from finmitra_person1.evidence.engine import EvidenceEngine, assess, build_evidence_bundle
from finmitra_person1.evidence.validation import validate_normalized_transactions
from finmitra_person1.evidence.grading import determine_grade, check_insufficient_history, compute_evidence_score
from finmitra_person1.evidence.confidence import compute_evidence_confidence
from finmitra_person1.evidence.anomaly import detect_anomalies


# --- 2. Schema Adversarial Tests ---

def test_schema_missing_borrower_id():
    with pytest.raises(ValidationError):
        BorrowerInput.model_validate({"sources": []})

def test_schema_missing_source_id():
    with pytest.raises(ValidationError):
        SourceInput.model_validate({"source_type": "BANK_STATEMENT", "records": []})

def test_schema_negative_amount_paise():
    with pytest.raises(ValidationError):
        NormalizedTransaction(
            transaction_id="TX1",
            date=date(2026, 1, 1),
            amount_paise=-100,
            direction="CREDIT",
            category=TransactionCategory.BUSINESS_INCOME,
            category_confidence=0.9,
            mode=TransactionMode.UPI,
            source=DataSourceType.UPI,
            verification=VerificationLevel.SOURCE_CONNECTED,
            category_source=CategorySource.MERCHANT_QR_MATCH,
            model_eligible=True,
        )

def test_schema_invalid_confidence_bounds():
    with pytest.raises(ValidationError):
        NormalizedTransaction(
            transaction_id="TX1",
            date=date(2026, 1, 1),
            amount_paise=1000,
            direction="CREDIT",
            category=TransactionCategory.BUSINESS_INCOME,
            category_confidence=1.5,
            mode=TransactionMode.UPI,
            source=DataSourceType.UPI,
            verification=VerificationLevel.SOURCE_CONNECTED,
            category_source=CategorySource.MERCHANT_QR_MATCH,
            model_eligible=True,
        )
    with pytest.raises(ValidationError):
        NormalizedTransaction(
            transaction_id="TX1",
            date=date(2026, 1, 1),
            amount_paise=1000,
            direction="CREDIT",
            category=TransactionCategory.BUSINESS_INCOME,
            category_confidence=-0.1,
            mode=TransactionMode.UPI,
            source=DataSourceType.UPI,
            verification=VerificationLevel.SOURCE_CONNECTED,
            category_source=CategorySource.MERCHANT_QR_MATCH,
            model_eligible=True,
        )

def test_schema_evidence_result_bounds():
    with pytest.raises(ValidationError):
        EvidenceResult(
            component="evidence",
            version="1.0.0",
            score=105.0,
            status="SUFFICIENT",
            confidence=0.8,
            evidence_grade="A",
            insufficient_history=False,
        )
    with pytest.raises(ValidationError):
        EvidenceResult(
            component="evidence",
            version="1.0.0",
            score=80.0,
            status="SUFFICIENT",
            confidence=-0.1,
            evidence_grade="A",
            insufficient_history=False,
        )

def test_schema_null_optional_fields():
    tx = NormalizedTransaction(
        transaction_id="TX_OPT",
        date=date(2026, 1, 15),
        amount_paise=50000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.9,
        mode=TransactionMode.UPI,
        source=DataSourceType.UPI,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        model_eligible=True,
        source_record_id=None,
        counterparty_id=None,
        counterparty_name=None,
        narration=None,
        duplicate_group_id=None,
        anomaly_score=None,
    )
    assert tx.counterparty_id is None
    assert tx.linked_transaction_ids == []


# --- 3. Money Correctness ---

def test_money_paise_parsing():
    assert parse_amount_to_paise(0) == 0
    assert parse_amount_to_paise(0.01) == 1
    assert parse_amount_to_paise(1) == 100
    assert parse_amount_to_paise(1850) == 185000
    assert parse_amount_to_paise("₹1,850.50") == 185050
    assert parse_amount_to_paise("1,00,000") == 10000000
    assert parse_amount_to_paise("10,00,00,000") == 10000000000  # 10 crore INR in paise (10,00,00,000 * 100)
    assert parse_amount_to_paise(None) is None
    assert parse_amount_to_paise("invalid") is None

def test_money_negative_amount_handling():
    assert parse_amount_to_paise(-500) == -50000
    # Negative amounts must be rejected during normalization
    raw = BorrowerInput(
        borrower_id="B_NEG",
        sources=[
            SourceInput(
                source_id="S1",
                source_type=DataSourceType.BANK_STATEMENT,
                records=[{"id": "R1", "date": "2026-01-01", "amount": -500, "type": "CREDIT"}]
            )
        ]
    )
    bundle = EvidenceEngine().process(raw)
    assert len(bundle.normalized_transactions) == 0
    assert len(bundle.result.reasons) > 0


# --- 4. Date Correctness ---

def test_date_parsing_edge_cases():
    assert parse_flexible_date("2024-02-29") == date(2024, 2, 29)  # Leap year
    assert parse_flexible_date("2026-02-29") is None  # Invalid leap year
    assert parse_flexible_date("31/12/2025") == date(2025, 12, 31)
    assert parse_flexible_date("2026-09-20T10:30:00Z") == date(2026, 9, 20)
    assert parse_flexible_date("invalid_date") is None

def test_date_future_quarantine():
    ref = date(2026, 9, 20)
    raw = BorrowerInput(
        borrower_id="B_FUTURE",
        sources=[
            SourceInput(
                source_id="S1",
                source_type=DataSourceType.BANK_STATEMENT,
                records=[
                    {"id": "R1", "date": "2026-09-15", "amount": 1000, "type": "CREDIT"},
                    {"id": "R2", "date": "2026-10-01", "amount": 2000, "type": "CREDIT"},  # Future date
                ]
            )
        ]
    )
    bundle = EvidenceEngine().process(raw, reference_date=ref)
    tx_ids = [t.transaction_id for t in bundle.normalized_transactions]
    assert "R1" in tx_ids
    assert "R2" not in tx_ids  # Quarantined due to future date!


# --- 5. Deduplication Attack Tests ---

def test_dedup_exact_id_duplicate():
    p1 = ProvenanceRecord(source_type=DataSourceType.UPI, source_id="S1", source_record_id="TX_DUP", raw_data_hash="abc")
    tx1 = NormalizedTransaction(
        transaction_id="TX_DUP",
        date=date(2026, 1, 1),
        amount_paise=100000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.9,
        mode=TransactionMode.UPI,
        source=DataSourceType.UPI,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        model_eligible=True,
        provenance=[p1],
    )
    tx2 = copy.deepcopy(tx1)
    deduped, conflicts, stats = run_deduplication([tx1, tx2])
    assert len(deduped) == 1
    assert stats["exact_duplicates"] == 1
    assert len(deduped[0].provenance) == 1  # Merged cleanly

def test_dedup_cross_source_linkage():
    # UPI credit matched with Bank statement settlement
    p_upi = ProvenanceRecord(source_type=DataSourceType.UPI, source_id="UPI_SRC", source_record_id="UPI_101", raw_data_hash="h1")
    p_bank = ProvenanceRecord(source_type=DataSourceType.BANK_STATEMENT, source_id="BNK_SRC", source_record_id="BANK_202", raw_data_hash="h2")
    
    tx_upi = NormalizedTransaction(
        transaction_id="UPI_101",
        date=date(2026, 1, 10),
        amount_paise=185000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.95,
        mode=TransactionMode.UPI,
        source=DataSourceType.UPI,
        verification=VerificationLevel.MERCHANT_MATCHED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        model_eligible=True,
        provenance=[p_upi],
        metadata={"utr": "UTR123456"}
    )
    tx_bank = NormalizedTransaction(
        transaction_id="BANK_202",
        date=date(2026, 1, 10),
        amount_paise=185000,
        direction="CREDIT",
        category=TransactionCategory.UNCLASSIFIED,
        category_confidence=0.25,
        mode=TransactionMode.BANK_TRANSFER,
        source=DataSourceType.BANK_STATEMENT,
        verification=VerificationLevel.SOURCE_CONNECTED,
        category_source=CategorySource.NONE,
        model_eligible=False,
        provenance=[p_bank],
        metadata={"utr": "UTR123456"}
    )
    deduped, conflicts, stats = run_deduplication([tx_upi, tx_bank])
    assert len(deduped) == 1
    assert stats["cross_source_matches"] == 1
    assert len(deduped[0].provenance) == 2
    # Strong evidence category from UPI must be preserved!
    assert deduped[0].category == TransactionCategory.BUSINESS_INCOME
    assert deduped[0].model_eligible is True

def test_dedup_legitimate_repeated_transactions():
    # Same amount, same day, different customers -> Must NOT be deduplicated
    tx1 = NormalizedTransaction(
        transaction_id="R1",
        date=date(2026, 1, 10),
        amount_paise=185000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.95,
        mode=TransactionMode.UPI,
        source=DataSourceType.UPI,
        verification=VerificationLevel.MERCHANT_MATCHED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        model_eligible=True,
        counterparty_name="Customer A",
        narration="Bill 001"
    )
    tx2 = NormalizedTransaction(
        transaction_id="R2",
        date=date(2026, 1, 10),
        amount_paise=185000,
        direction="CREDIT",
        category=TransactionCategory.BUSINESS_INCOME,
        category_confidence=0.95,
        mode=TransactionMode.UPI,
        source=DataSourceType.UPI,
        verification=VerificationLevel.MERCHANT_MATCHED,
        category_source=CategorySource.MERCHANT_QR_MATCH,
        model_eligible=True,
        counterparty_name="Customer B",
        narration="Bill 002"
    )
    deduped, conflicts, stats = run_deduplication([tx1, tx2])
    assert len(deduped) == 2  # Both preserved!


# --- 7. Business-Income Classification Attack ---

def test_unclassified_credit_not_business_income():
    raw_rec = BorrowerInput(
        borrower_id="B_ATTACK",
        sources=[
            SourceInput(
                source_id="S1",
                source_type=DataSourceType.BANK_STATEMENT,
                records=[
                    {"id": "T1", "date": "2026-01-15", "amount": 50000, "type": "CREDIT", "narration": "UPI/1234/Payment from Ramesh"},
                    {"id": "T2", "date": "2026-01-16", "amount": 30000, "type": "CREDIT", "narration": "BY CASH DEPOSIT"},
                ]
            )
        ]
    )
    bundle = EvidenceEngine().process(raw_rec)
    txs = {t.transaction_id: t for t in bundle.normalized_transactions}
    
    # Generic ₹50,000 credit without merchant evidence must be UNCLASSIFIED and NOT model_eligible
    assert txs["T1"].category == TransactionCategory.UNCLASSIFIED
    assert txs["T1"].model_eligible is False

    # Cash deposit without evidence must be CASH_DEPOSIT and NOT model_eligible
    assert txs["T2"].category == TransactionCategory.CASH_DEPOSIT
    assert txs["T2"].model_eligible is False


# --- 9. Self-Declared Cash Attack ---

def test_self_declared_cash_policy():
    # Uncorroborated self-declared cash
    raw = BorrowerInput(
        borrower_id="B_SELF",
        sources=[
            SourceInput(
                source_id="S_DECL",
                source_type=DataSourceType.SELF_DECLARATION,
                records=[{"id": "SD1", "date": "2026-01-10", "amount": 80000, "type": "CREDIT", "category": "SELF_DECLARED_CASH_INCOME"}]
            )
        ]
    )
    bundle = EvidenceEngine().process(raw)
    assert len(bundle.normalized_transactions) == 1
    t = bundle.normalized_transactions[0]
    assert t.category == TransactionCategory.SELF_DECLARED_CASH_INCOME
    assert t.verification == VerificationLevel.SELF_DECLARED
    assert t.model_eligible is False

def test_self_declared_cash_corroboration_upgrade():
    # Self declared cash corroborated by Invoice
    raw = BorrowerInput(
        borrower_id="B_SELF_CORROB",
        sources=[
            SourceInput(
                source_id="S_DECL",
                source_type=DataSourceType.SELF_DECLARATION,
                records=[{"id": "SD1", "date": "2026-01-10", "amount": 80000, "type": "CREDIT", "ref_no": "INV-800"}]
            ),
            SourceInput(
                source_id="S_INV",
                source_type=DataSourceType.INVOICE,
                records=[{"id": "INV1", "date": "2026-01-10", "amount": 80000, "type": "CREDIT", "ref_no": "INV-800"}]
            )
        ]
    )
    bundle = EvidenceEngine().process(raw)
    assert len(bundle.normalized_transactions) == 1
    t = bundle.normalized_transactions[0]
    # Should be upgraded to BUSINESS_INCOME, DOCUMENT_MATCHED, model_eligible=True
    assert t.category == TransactionCategory.BUSINESS_INCOME
    assert t.verification == VerificationLevel.DOCUMENT_MATCHED
    assert t.model_eligible is True


# --- 10. Transfer Detection ---

def test_transfer_detection_scenarios():
    raw = BorrowerInput(
        borrower_id="Rajesh Kumar",
        business_name="Rajesh Trading Co",
        sources=[
            SourceInput(
                source_id="S1",
                source_type=DataSourceType.BANK_STATEMENT,
                records=[
                    {"id": "TR1", "date": "2026-01-05", "amount": 25000, "type": "DEBIT", "narration": "Self transfer to savings A/C"},
                    {"id": "TR2", "date": "2026-01-06", "amount": 50000, "type": "CREDIT", "counterparty": "Rajesh Kumar"},
                ]
            )
        ]
    )
    bundle = EvidenceEngine().process(raw)
    for t in bundle.normalized_transactions:
        assert t.category == TransactionCategory.TRANSFER
        assert t.model_eligible is False


# --- 12. Conflict Testing ---

def test_cross_source_amount_mismatch_conflict():
    raw = BorrowerInput(
        borrower_id="B_CONFLICT",
        sources=[
            SourceInput(
                source_id="BANK",
                source_type=DataSourceType.BANK_STATEMENT,
                records=[{"id": "B1", "date": "2026-01-10", "amount": 50000, "type": "CREDIT", "ref_no": "REF-999"}]
            ),
            SourceInput(
                source_id="UPI",
                source_type=DataSourceType.UPI,
                records=[{"id": "U1", "date": "2026-01-10", "amount": 5000, "type": "CREDIT", "ref_no": "REF-999"}]
            )
        ]
    )
    bundle = EvidenceEngine().process(raw)
    assert len(bundle.conflicts) > 0
    assert bundle.conflicts[0].conflict_type == ConflictType.AMOUNT_MISMATCH


# --- 16 & 17. Grade & History Boundaries ---

def test_grade_boundaries():
    assert determine_grade(85.0) == "A"
    assert determine_grade(84.999) == "B"
    assert determine_grade(70.0) == "B"
    assert determine_grade(69.999) == "C"
    assert determine_grade(50.0) == "C"
    assert determine_grade(49.999) == "D"

def test_insufficient_history_boundaries():
    assert check_insufficient_history(89, 3, 30) is True
    assert check_insufficient_history(90, 3, 30) is False
    assert check_insufficient_history(91, 3, 30) is False
    assert check_insufficient_history(90, 2, 30) is True
    assert check_insufficient_history(90, 3, 29) is True


# --- 20. Pipeline Resilience ---

def test_pipeline_resilience():
    # 100 valid txns, 10 malformed, 5 duplicates, 3 conflicts, 2 self-declared, 1 anomaly
    records = []
    start_date = date(2026, 1, 1)
    for i in range(100):
        d = start_date + timedelta(days=i)
        records.append({"id": f"V_{i}", "date": d.strftime("%Y-%m-%d"), "amount": 1000 + (i * 10), "type": "CREDIT", "category": "BUSINESS_INCOME", "qr_collection": True})
    
    # 10 malformed
    for i in range(10):
        records.append({"id": f"M_{i}", "date": "invalid_date", "amount": "bad_amount"})
    
    # 5 duplicates
    for i in range(5):
        records.append({"id": f"V_{i}", "date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), "amount": 1000 + (i * 10), "type": "CREDIT"})

    # 1 anomaly
    records.append({"id": "ANO_1", "date": "2026-03-01", "amount": 5000000, "type": "CREDIT", "qr_collection": True})

    raw = BorrowerInput(
        borrower_id="B_RESILIENT",
        sources=[
            SourceInput(source_id="SRC_RES", source_type=DataSourceType.BANK_STATEMENT, records=records),
            SourceInput(
                source_id="SRC_SELF",
                source_type=DataSourceType.SELF_DECLARATION,
                records=[
                    {"id": "SD_1", "date": "2026-02-01", "amount": 40000, "type": "CREDIT"},
                    {"id": "SD_2", "date": "2026-02-02", "amount": 45000, "type": "CREDIT"},
                ]
            )
        ]
    )

    bundle = EvidenceEngine().process(raw)
    assert isinstance(bundle, EvidenceBundle)
    assert bundle.result.status in ("SUFFICIENT", "DEGRADED", "INSUFFICIENT")
    assert len(bundle.normalized_transactions) > 0


# --- 22. Determinism Test ---

def test_determinism():
    fixture_path = Path("fixtures/messy_multi_source/input.json")
    if not fixture_path.exists():
        pytest.skip("Fixture not found")
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    borrower = BorrowerInput.model_validate(data)
    engine = EvidenceEngine()

    outputs = []
    for _ in range(5):
        bundle = engine.process(borrower)
        dict_repr = bundle.model_dump(mode="json")
        outputs.append(json.dumps(dict_repr, sort_keys=True))
    
    # All 5 runs must yield 100% identical outputs!
    for i in range(1, 5):
        assert outputs[i] == outputs[0], f"Determinism failure between run 0 and run {i}"
