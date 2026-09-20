"""Versioned configuration for the standalone cash-flow engine."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "data" / "generated" / "borrowers.jsonl"
TRAINING_MATRIX_PATH = ROOT / "data" / "processed" / "training_matrix.csv"
ARTIFACT_PATH = ROOT / "artifacts" / "cashflow_stress_hist_gradient_boosting_v2.joblib"
METADATA_PATH = ROOT / "artifacts" / "cashflow_stress_hist_gradient_boosting_v2.json"
GLOBAL_IMPORTANCE_PATH = ROOT / "artifacts" / "global_importance_v1.csv"

RANDOM_SEED = 42
FEATURE_VERSION = "2.0.0-original12"
MODEL_VERSION = "hist-gradient-boosting-2.0.0"
OBSERVATION_MONTHS = 24
TARGET_MONTHS = 3
MIN_ACTIVE_MONTHS = 3
MIN_VALID_TRANSACTIONS = 30
SUFFICIENT_ACTIVE_MONTHS = 6
SUFFICIENT_VALID_TRANSACTIONS = 60

OPERATING_INFLOW_CATEGORIES = frozenset(
    {"BUSINESS_INCOME", "MARKETPLACE_SETTLEMENT", "POS_SETTLEMENT", "SUPPORTED_CASH_SALES"}
)
OPERATING_OUTFLOW_CATEGORIES = frozenset(
    {"BUSINESS_EXPENSE", "INVENTORY", "SUPPLIER_PURCHASE", "OPERATING_FEE", "BUSINESS_SERVICE", "BUSINESS_UTILITY"}
)
FINANCING_CATEGORIES = frozenset({"LOAN_DISBURSEMENT", "LOAN_REPAYMENT"})
EXCLUDED_REVENUE_CATEGORIES = frozenset(
    {"TRANSFER", "SELF_TRANSFER", "LOAN_DISBURSEMENT", "REFUND", "SELF_DECLARED_CASH_INCOME"}
)
