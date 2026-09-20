# FinMitra — Person 1 (Evidence Engine + Ingestion + Normalization)

FinMitra is an explainable AI-powered credit assessment platform designed for micro-enterprises, thin-file borrowers, and small businesses in emerging markets.

This repository contains **Person 1's complete subsystem**: the **Evidence Engine, Data Ingestion, and Normalization Layer**.

---

## 1. FinMitra 4-Engine Architecture

```text
                    BORROWER DATA
           (Bank, UPI, POS, Ledgers, Invoices)
                         │
                         ▼
                ┌─────────────────┐
                │  PERSON 1       │
                │ Evidence Engine │
                └────────┬────────┘
                         │
              normalized + evidence-
                tagged transaction data
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     Person 2        Person 3        Person 4
     Cash Flow       Repayment        Capacity
        ML            Engine           Engine
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                 PROFILE ASSEMBLER
                         │
                         ▼
             FINMITRA CREDIT EVIDENCE
                    PROFILE
```

- **Person 1 (Evidence Engine)**: *"Is the borrower's financial evidence reliable, complete, consistent, and trustworthy?"*
- **Person 2 (Cash Flow ML)**: *"How healthy and stable is the borrower's cash flow?"*
- **Person 3 (Repayment Engine)**: *"How reliably has the borrower repaid formal and informal debt?"*
- **Person 4 (Capacity & Affordability)**: *"Can the borrower safely afford new credit?"*

---

## 2. Core Capabilities of Person 1

1. **Heterogeneous Ingestion**: Ingests JSON and CSV data from bank statements, merchant UPI QRs, POS card swipe batches, e-commerce marketplaces, digital ledgers (Khatabook/Vyapar), supplier invoices, cash receipts, and self-declarations.
2. **Canonical Normalization**: Standardizes diverse inputs into `NormalizedTransaction` objects with amounts strictly in non-negative integer paise.
3. **Evidence-Driven Classification**: Business revenue and expenses are classified only when backed by concrete evidence (merchant QRs, matching invoices, ledger links, or marketplace settlements). Generic or unverified transfers remain `UNCLASSIFIED`.
4. **Self-Declared Cash Income Isolation**: Preserves self-declared cash revenue claims but marks them with `model_eligible = False` and `VerificationLevel.SELF_DECLARED` so predictive models are never corrupted by unverified assertions.
5. **3-Level Deduplication & Provenance**: Detects exact ID duplicates, strong fingerprint duplicates, and cross-source settlement matches without erasing source traceability (`provenance` array).
6. **Conflict & Anomaly Detection**: Detects amount/date mismatches across sources. Flags statistical and behavioral outliers (`anomaly_flag = True`) without discarding legitimate high-value transactions.
7. **Evidence Scoring & Grading**: Computes a transparent 0–100 evidence quality score, maps it to an evidence grade (`A`, `B`, `C`, `D`), calculates statistical confidence (`0.0–1.0`), detects thin files (`insufficient_history`), and emits explainable `EVxx` reason codes.

---

## 3. Scope Boundary (What Person 1 Does NOT Do)

- Does **not** predict credit default or forecast future revenue.
- Does **not** calculate borrower repayment scores or on-time percentages.
- Does **not** calculate debt-to-income (DTI), safe EMI, or max loan principal.
- Does **not** make final credit grant decisions.

---

## 4. Installation

```bash
# Clone or navigate to the directory
cd finmitra_person1

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 5. CLI Usage

The CLI outputs clean, deterministic JSON strictly to `stdout`, while human-readable diagnostic logs are routed to `stderr`.

### Run on Canonical Synthetic Fixtures

```bash
# 1. Strong Multi-Source Kirana Store
python3 run_evidence.py --input fixtures/strong_borrower/input.json --pretty

# 2. Seasonal Agricultural Enterprise (Farmer)
python3 run_evidence.py --input fixtures/seasonal_farmer/input.json --pretty

# 3. Thin-File Street Vendor (<90 days history)
python3 run_evidence.py --input fixtures/thin_file/input.json --pretty

# 4. Messy Multi-Source Dataset (Duplicates, Conflicts, Self-Declared Cash, Anomalies)
python3 run_evidence.py --input fixtures/messy_multi_source/input.json --pretty
```

### Save Output to File

```bash
python3 run_evidence.py --input fixtures/strong_borrower/input.json --output /tmp/output.json
```

---

## 6. Running Tests

The test suite includes 38 comprehensive tests covering schemas, ingestion adapters, normalization, categorization, deduplication, provenance, validation, scoring, confidence, synthetic fixtures, integration, and architectural boundaries.

```bash
python3 -m pytest -v
```

---

## 7. Example Output Structure

```json
{
  "borrower_id": "BORR-KIRANA-001",
  "result": {
    "component": "evidence",
    "version": "1.0.0",
    "score": 85.64,
    "status": "SUFFICIENT",
    "confidence": 0.7768,
    "evidence_grade": "A",
    "insufficient_history": false,
    "features": {
      "coverage_days": 200,
      "active_months": 7,
      "raw_transaction_count": 38,
      "normalized_transaction_count": 38,
      "valid_transaction_count": 38,
      "duplicate_transaction_count": 0,
      "cross_source_match_count": 10,
      "conflict_count": 0,
      "verified_transaction_count": 34,
      "unclassified_transaction_count": 4,
      "self_declared_transaction_count": 0,
      "source_count": 4
    },
    "reasons": [
      {
        "code": "EV04",
        "direction": "POSITIVE",
        "impact": 10.0,
        "message": "10 cross-source transaction pairs matched (e.g. UPI collections matched with bank settlements)."
      },
      {
        "code": "EV08",
        "direction": "POSITIVE",
        "impact": 5.0,
        "message": "Financial data successfully ingested from 4 distinct data sources."
      },
      {
        "code": "EV10",
        "direction": "POSITIVE",
        "impact": 15.0,
        "message": "34 transactions verified against digital business ledgers, merchant QR registrations, or invoices."
      },
      {
        "code": "EV16",
        "direction": "POSITIVE",
        "impact": 5.0,
        "message": "100% of ingested records passed strict schema and chronological validation."
      }
    ],
    "warnings": []
  },
  "normalized_transactions": [
    {
      "transaction_id": "BNK-001",
      "date": "2026-01-05",
      "amount_paise": 2500000,
      "direction": "DEBIT",
      "category": "BUSINESS_EXPENSE",
      "category_confidence": 1.0,
      "mode": "BANK_TRANSFER",
      "source": "BANK_STATEMENT",
      "verification": "CROSS_SOURCE_CORROBORATED",
      "category_source": "CROSS_SOURCE_MATCH",
      "model_eligible": true,
      "provenance": [
        {
          "source_type": "BANK_STATEMENT",
          "source_id": "BANK-HDFC-01",
          "source_record_id": "BNK-001"
        },
        {
          "source_type": "INVOICE",
          "source_id": "INV-SUPP-01",
          "source_record_id": "INV-HUL-101"
        }
      ]
    }
  ],
  "source_summary": {
    "source_count": 4,
    "sources": [
      {"source_id": "BANK-HDFC-01", "source_type": "BANK_STATEMENT", "record_count": 20},
      {"source_id": "UPI-PAYTM-01", "source_type": "QR", "record_count": 8},
      {"source_id": "INV-SUPP-01", "source_type": "INVOICE", "record_count": 6},
      {"source_id": "LEDGER-KHATA-01", "source_type": "BUSINESS_LEDGER", "record_count": 4}
    ],
    "raw_error_count": 0
  },
  "conflicts": []
}
```

---

## 8. Key Architectural Design Decisions

1. **Self-Declared Cash Separation**: In emerging markets, borrowers frequently claim cash sales. Person 1 accepts and preserves these claims under `SELF_DECLARED_CASH_INCOME` but sets `model_eligible = False`. They are only upgraded if corroborating physical receipts or ledger proofs exist.
2. **Provenance Never Erased**: When deduplication merges multiple raw records into one canonical economic event, the `provenance` array retains references to all raw records.
3. **Anomaly != Invalidity**: Outlier transactions (e.g. bulk seasonal sales) are flagged with `anomaly_flag = True` and generate explainable `EV11` warnings rather than being deleted.
4. **Explainability Over Cleverness**: Categorization and grading rely on deterministic rules, explicit weights, and documented policies rather than opaque heuristics.
