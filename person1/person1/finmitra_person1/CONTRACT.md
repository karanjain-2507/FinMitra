# FinMitra Subsystem Contract — Person 1 (Evidence Engine)

## 1. Subsystem Purpose & Boundary

Person 1 is responsible for answering:
> **"Is the borrower's financial evidence reliable, consistent, sufficiently complete, and trustworthy?"**

### Responsibilities
- Ingesting heterogeneous financial sources (Bank Statements, UPI collections, POS settlements, E-commerce Marketplaces, Digital Ledgers, Invoices, Receipts, and Self-Declarations).
- Normalizing records into a standardized canonical transaction timeline.
- Deterministic data validation and quarantine of malformed records.
- 3-level deduplication preserving full source provenance.
- Explainable, evidence-backed categorization (Merchant QR, Invoices, Ledgers, Marketplace, Transfers, Cash).
- Explicit isolation of **Self-Declared Cash Income** (`model_eligible = False`).
- Statistical and behavioral anomaly flagging without silent record deletion.
- Multi-dimensional evidence quality scoring (0–100) and grade assignment (A, B, C, D).
- Statistical evidence confidence computation (0.0–1.0).
- Insufficient history detection.
- Emitting explainable `EVxx` reason codes.

### Out of Scope (Owned by Persons 2, 3, 4)
- Person 1 does **NOT** predict defaults or cash flow trajectories (Person 2).
- Person 1 does **NOT** calculate repayment performance scores or debt block policies (Person 3).
- Person 1 does **NOT** calculate safe EMI, max loan principal, affordability, or final credit readiness index (Person 4).

---

## 2. Ingestion Contracts (Input)

### `BorrowerInput`
```python
class BorrowerInput(BaseModel):
    borrower_id: str
    business_name: Optional[str] = None
    sources: List[SourceInput] = []
    metadata: Dict[str, Any] = {}
```

### `SourceInput`
```python
class SourceInput(BaseModel):
    source_id: str
    source_type: DataSourceType
    records: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}
```

### Supported `DataSourceType` Enums
| Source Type | Description |
| :--- | :--- |
| `BANK_STATEMENT` | Savings or current bank account statement |
| `UPI` | UPI transaction statement or aggregator logs |
| `QR` | Static or dynamic merchant QR transaction logs |
| `POS` | Point of Sale (EDC) card swipe settlements |
| `MARKETPLACE` | E-commerce / aggregator payouts (Amazon, Swiggy, Zomato, etc.) |
| `BUSINESS_LEDGER` | Digital business ledgers (Khatabook, Vyapar, Tally) |
| `INVOICE` | Customer or supplier tax invoices |
| `SUPPLIER_RECORD` | Supplier delivery slips or purchase registers |
| `RECEIPT` | Physical retail receipt or counter cash bill |
| `CASH_RECORD` | Cash register records |
| `SELF_DECLARATION` | Self-reported unverified revenue claims |
| `OTHER` | Generic or unclassified source payload |

---

## 3. Canonical Transaction Model (`NormalizedTransaction`)

Every ingested raw record is normalized into `NormalizedTransaction`:

```python
class NormalizedTransaction(BaseModel):
    transaction_id: str
    date: date
    amount_paise: int  # Must be non-negative integer paise (1 INR = 100 paise)
    direction: Literal["CREDIT", "DEBIT"]

    category: TransactionCategory
    category_confidence: float  # 0.0 <= confidence <= 1.0

    mode: TransactionMode

    source: DataSourceType
    source_record_id: Optional[str] = None

    verification: VerificationLevel
    category_source: CategorySource

    counterparty_id: Optional[str] = None
    counterparty_name: Optional[str] = None

    narration: Optional[str] = None

    status: TransactionStatus = TransactionStatus.SUCCESS

    duplicate_group_id: Optional[str] = None
    linked_transaction_ids: List[str] = []

    model_eligible: bool
    anomaly_flag: bool = False
    anomaly_score: Optional[float] = None

    provenance: List[ProvenanceRecord] = []
    metadata: Dict[str, Any] = {}
```

### Field Definitions
- `amount_paise`: Integer representation of currency (e.g. ₹1,850.50 is stored as `185050`). Prevents floating-point rounding errors.
- `direction`: `CREDIT` (money received by borrower) or `DEBIT` (money paid out).
- `model_eligible`: Boolean flag indicating whether downstream predictive ML models (Person 2) should include this transaction in revenue/expense calculations. `False` for duplicates, internal transfers, and uncorroborated self-declared cash income.
- `anomaly_flag`: Set to `True` if transaction is a statistical outlier (IQR / Z-score / Isolation Forest).
- `provenance`: Array of `ProvenanceRecord` detailing the exact origin source ID, record ID, and raw content hash.

---

## 4. Verification Semantics (`VerificationLevel`)

| Level | Semantic Meaning |
| :--- | :--- |
| `SOURCE_CONNECTED` | Originates from a connected digital account or API feed (does **not** guarantee factual business purpose without corroborating context). |
| `CROSS_SOURCE_CORROBORATED` | Matched and corroborated across two or more independent financial sources (e.g. Bank credit matches UPI log). |
| `DOCUMENT_MATCHED` | Corroborated against an invoice or physical receipt. |
| `LEDGER_MATCHED` | Corroborated against an independent digital ledger entry. |
| `MERCHANT_MATCHED` | Verified as originating through a registered merchant QR or POS terminal ID. |
| `SELF_DECLARED` | Borrower-asserted claim without independent digital verification. |
| `UNVERIFIED` | Originates from an unverified or informal single source. |

---

## 5. Category Semantics (`TransactionCategory` & `CategorySource`)

| Category | Description | Typical Category Source |
| :--- | :--- | :--- |
| `BUSINESS_INCOME` | Verified business revenue | `MERCHANT_QR_MATCH`, `INVOICE_MATCH`, `LEDGER_MATCH` |
| `BUSINESS_EXPENSE` | Verified business operational cost | `INVOICE_MATCH`, `COUNTERPARTY_PATTERN` |
| `HOUSEHOLD_EXPENSE` | Personal / domestic expenditure | `NARRATION_RULE` |
| `TRANSFER` | Internal / own-account transfer | `NARRATION_RULE`, `COUNTERPARTY_PATTERN` |
| `LOAN_DISBURSEMENT` | Inflow from loan disbursement | `NARRATION_RULE` |
| `LOAN_REPAYMENT` | Outflow for formal loan EMI | `NARRATION_RULE` |
| `INFORMAL_LOAN` | Inflow/outflow from informal credit (chit/bisi/lender) | `NARRATION_RULE` |
| `MARKETPLACE_SETTLEMENT`| Payout from e-commerce marketplace | `MARKETPLACE_SETTLEMENT` |
| `POS_SETTLEMENT` | Settlement from card swipe terminal | `POS_MERCHANT_MATCH` |
| `CASH_DEPOSIT` | Bank cash deposit (uncorroborated) | `NARRATION_RULE` |
| `CASH_WITHDRAWAL` | Bank cash withdrawal | `NARRATION_RULE` |
| `FEE` | Bank or platform charges / MDR fees | `NARRATION_RULE` |
| `TAX` | GST or direct tax challan payment | `NARRATION_RULE` |
| `REFUND` | Reversal or return of earlier transaction | `NARRATION_RULE` |
| `SAVINGS` | Sweep or transfer to savings instrument | `NARRATION_RULE` |
| `SELF_DECLARED_CASH_INCOME` | Self-reported unverified cash sales | `SELF_DECLARED` |
| `UNCLASSIFIED` | Transaction with weak/ambiguous evidence | `NONE` |
| `OTHER` | Miscellaneous categorized event | `NARRATION_RULE` |

---

## 6. Output Contract: `EvidenceBundle` & `EvidenceResult`

### `EvidenceResult`
```python
class EvidenceResult(BaseModel):
    component: Literal["evidence"] = "evidence"
    version: str

    score: Optional[float]  # 0.0 to 100.0 evidence quality score
    status: Literal["SUFFICIENT", "DEGRADED", "INSUFFICIENT"]

    confidence: float       # 0.0 to 1.0 statistical confidence

    evidence_grade: Literal["A", "B", "C", "D"]
    insufficient_history: bool

    features: Dict[str, Any]
    reasons: List[Reason]
    warnings: List[str]
```

### Grade Policy
- **Grade A** (`>= 85.0`): Strong, diverse multi-source evidence, high corroboration, minimal conflicts.
- **Grade B** (`70.0 – 84.99`): Reliable evidence with moderate source diversity and solid validity.
- **Grade C** (`50.0 – 69.99`): Single source or partial gaps in history/corroboration.
- **Grade D** (`< 50.0`): Low evidence reliability, thin file, or severe conflicts.

> **Note**: An evidence grade is **NOT** a credit score or default risk rating. A Grade D means "we lack sufficient high-quality evidence", not "the borrower is bad".

---

## 7. Standard Reason Codes (`EVxx`)

| Code | Name | Direction | Meaning |
| :--- | :--- | :--- | :--- |
| `EV01` | `malformed_record` | `NEGATIVE` | Malformed raw record quarantined. |
| `EV02` | `missing_required_field` | `NEGATIVE` | Critical transaction fields missing. |
| `EV03` | `duplicate_record` | `NEUTRAL` | Duplicate record identified and linked. |
| `EV04` | `cross_source_duplicate` | `POSITIVE` | Cross-source economic event match confirmed. |
| `EV05` | `conflicting_records` | `NEGATIVE` | Discrepancy (e.g. amount mismatch) found across sources. |
| `EV06` | `unclassified_transaction` | `NEUTRAL` | Ambiguous transaction left unclassified. |
| `EV07` | `self_declared_cash_excluded` | `NEUTRAL` | Self-declared cash isolated and excluded from model. |
| `EV08` | `source_connected` | `POSITIVE` | Data successfully ingested from connected digital source. |
| `EV09` | `cross_source_corroborated`| `POSITIVE` | Record corroborated by secondary source. |
| `EV10` | `document_or_ledger_match`| `POSITIVE` | Verified against invoice, physical receipt, or ledger. |
| `EV11` | `anomaly_detected` | `NEGATIVE` | Outlier transaction flagged for review. |
| `EV12` | `insufficient_history` | `NEGATIVE` | History shorter than policy minimum (90 days / 3 months / 30 txns). |
| `EV13` | `low_source_coverage` | `NEGATIVE` | Single uncorroborated data source. |
| `EV14` | `transfer_detected` | `NEUTRAL` | Internal fund transfer isolated. |
| `EV15` | `unsupported_or_unknown_source` | `NEGATIVE` | Source schema unverified. |
| `EV16` | `high_data_completeness` | `POSITIVE` | 100% record validity and complete required metadata. |
| `EV17` | `multi_source_corroboration_strong` | `POSITIVE` | Strong multi-source corroboration integrity. |

---

## 8. Downstream Integration Contracts

### To Person 2 (Cash Flow ML Engine)
- Person 2 consumes: `EvidenceBundle.normalized_transactions`.
- Person 2 filters by `model_eligible == True` to train and infer cash flow stability without pollution from duplicates, internal transfers, or unverified cash claims.
- Person 2 uses `anomaly_flag` as a feature or warning indicator.

### To Person 3 (Repayment Engine)
- Person 3 consumes: `EvidenceBundle.normalized_transactions`.
- Person 3 queries transactions where `category in ("LOAN_REPAYMENT", "LOAN_DISBURSEMENT", "INFORMAL_LOAN")` to construct obligation schedules, check on-time repayment behavior, and evaluate informal debt pressure.

### To Person 4 (Capacity & Profile Assembler)
- Person 4 consumes: `EvidenceResult`.
- Person 4 uses `evidence_grade`, `insufficient_history`, `confidence`, and `score` to calibrate the borrower's overall credit profile and assign confidence weighting to the final recommendation.

---

## 9. Global Conventions

- **Dates**: Strict ISO 8601 (`YYYY-MM-DD`).
- **Currency**: Indian Rupee (`INR`).
- **Monetary Amounts**: Strictly integer paise (`amount_paise: int`).
- **Confidence & Ratios**: Strictly float between `0.0` and `1.0`.
- **Scores**: Strictly float between `0.0` and `100.0`.
- **Missing Numerics**: `None` (never substitute `0` for missing values).
- **Random Seed**: `42` (for deterministic anomaly detection).
