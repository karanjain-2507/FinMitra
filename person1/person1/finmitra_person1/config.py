"""
Centralized Configuration and Policies for FinMitra Person 1 Evidence Engine.
All thresholds, grading boundaries, scoring weights, and constants live here.
"""
from __future__ import annotations
from typing import Dict, Any


# Engine Metadata
ENGINE_NAME: str = "finmitra-person1-evidence"
ENGINE_VERSION: str = "1.0.0"
RANDOM_SEED: int = 42

# History Sufficiency Policy
MIN_HISTORY_DAYS: int = 90
MIN_ACTIVE_MONTHS: int = 3
MIN_VALID_TRANSACTIONS: int = 30

# Grading Boundaries (0-100 scale)
GRADE_A_MIN: float = 85.0
GRADE_B_MIN: float = 70.0
GRADE_C_MIN: float = 50.0

# Evidence Status Thresholds
STATUS_SUFFICIENT_MIN_SCORE: float = 70.0
STATUS_DEGRADED_MIN_SCORE: float = 50.0

# Multi-dimensional Quality Scoring Weights (Sum = 1.0)
WEIGHT_SOURCE_QUALITY: float = 0.25       # Diversity, reliability of connected sources
WEIGHT_CORROBORATION: float = 0.25        # Cross-source corroboration rate
WEIGHT_DATA_COMPLETENESS: float = 0.20    # Missing fields, valid vs invalid ratio
WEIGHT_CONSISTENCY_CONFLICT: float = 0.15 # Penalties for amount/date conflicts
WEIGHT_CLASSIFICATION_QUALITY: float = 0.10 # Proportion of confident vs unclassified txns
WEIGHT_DEDUP_INTEGRITY: float = 0.05      # Accurate duplicate grouping without leakage

# Deduplication & Corroboration Tolerances
CROSS_SOURCE_WINDOW_DAYS: int = 2
DEDUP_AMOUNT_TOLERANCE_PCT: float = 0.02  # 2% tolerance for fee deduction (e.g., POS/UPI charges)

# Anomaly Detection Settings
ANOMALY_ZSCORE_THRESHOLD: float = 3.5
ANOMALY_IQR_MULTIPLIER: float = 3.0
ISOLATION_FOREST_CONTAMINATION: float = 0.03
ISOLATION_FOREST_MIN_SAMPLES: int = 25

# Classification Confidence Baselines
CONFIDENCE_MERCHANT_QR: float = 0.95
CONFIDENCE_POS_SETTLEMENT: float = 0.92
CONFIDENCE_INVOICE_MATCH: float = 0.94
CONFIDENCE_LEDGER_MATCH: float = 0.90
CONFIDENCE_MARKETPLACE: float = 0.95
CONFIDENCE_COUNTERPARTY_PATTERN: float = 0.75
CONFIDENCE_NARRATION_RULE: float = 0.65
CONFIDENCE_SELF_DECLARED: float = 0.95    # Confidently known to be self-declared, but model_eligible=False
CONFIDENCE_UNCLASSIFIED: float = 0.25

# Standard EVxx Reason Codes Catalog
REASON_CODES: Dict[str, Dict[str, Any]] = {
    "EV01": {
        "name": "malformed_record",
        "direction": "NEGATIVE",
        "default_message": "Malformed raw record detected and quarantined."
    },
    "EV02": {
        "name": "missing_required_field",
        "direction": "NEGATIVE",
        "default_message": "Required transaction fields (e.g. date, amount) are missing."
    },
    "EV03": {
        "name": "duplicate_record",
        "direction": "NEUTRAL",
        "default_message": "Duplicate transaction record identified and grouped."
    },
    "EV04": {
        "name": "cross_source_duplicate",
        "direction": "POSITIVE",
        "default_message": "Cross-source economic event match identified (e.g. bank settlement for UPI payment)."
    },
    "EV05": {
        "name": "conflicting_records",
        "direction": "NEGATIVE",
        "default_message": "Material conflict detected across data sources (e.g. amount or date discrepancy)."
    },
    "EV06": {
        "name": "unclassified_transaction",
        "direction": "NEUTRAL",
        "default_message": "Transaction lacks sufficient evidence for definitive business classification."
    },
    "EV07": {
        "name": "self_declared_cash_excluded",
        "direction": "NEUTRAL",
        "default_message": "Self-declared cash income preserved separately and excluded from model eligibility until verified."
    },
    "EV08": {
        "name": "source_connected",
        "direction": "POSITIVE",
        "default_message": "Transaction originates directly from connected digital financial rail."
    },
    "EV09": {
        "name": "cross_source_corroborated",
        "direction": "POSITIVE",
        "default_message": "Transaction corroborated by independent secondary data source."
    },
    "EV10": {
        "name": "document_or_ledger_match",
        "direction": "POSITIVE",
        "default_message": "Transaction verified against digital business ledger or supplier/customer invoice."
    },
    "EV11": {
        "name": "anomaly_detected",
        "direction": "NEGATIVE",
        "default_message": "Transaction value is a statistical outlier compared to borrower's standard pattern."
    },
    "EV12": {
        "name": "insufficient_history",
        "direction": "NEGATIVE",
        "default_message": "Transaction history length or record volume is below the minimum threshold for confident assessment."
    },
    "EV13": {
        "name": "low_source_coverage",
        "direction": "NEGATIVE",
        "default_message": "Evidence is limited to a single uncorroborated or informal source."
    },
    "EV14": {
        "name": "transfer_detected",
        "direction": "NEUTRAL",
        "default_message": "Internal / own-account fund transfer detected and isolated from revenue."
    },
    "EV15": {
        "name": "unsupported_or_unknown_source",
        "direction": "NEGATIVE",
        "default_message": "Data source could not be verified against recognized financial schemas."
    },
    "EV16": {
        "name": "high_data_completeness",
        "direction": "POSITIVE",
        "default_message": "High record validity and complete required metadata across all sources."
    },
    "EV17": {
        "name": "multi_source_corroboration_strong",
        "direction": "POSITIVE",
        "default_message": "Extensive multi-source corroboration provides strong evidence integrity."
    }
}
