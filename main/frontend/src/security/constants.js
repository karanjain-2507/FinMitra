/** Snapshot and envelope constants. No secrets live here. */

export const SCHEMA_VERSION = "1.0.0"
export const PURPOSE = "FINMITRA_SUMMARY_TRANSFER"
export const ENVELOPE_VERSION = "1"
export const ALGORITHM = "AES-256-GCM"
export const KDF = "PBKDF2-SHA-256"
export const PBKDF2_ITERATIONS = 210_000
export const SALT_BYTES = 16
export const IV_BYTES = 12
export const KEY_BITS = 256
export const CONTENT_TYPE = "application/json; charset=utf-8"
export const MAX_PLAINTEXT_BYTES = 4096
export const MAX_QR_CHARS = 1800

export const DEFAULT_TTL_MS = 24 * 60 * 60 * 1000

export const EXPIRY_OPTIONS = [
  { id: "1h", label: "1 hour", ms: 60 * 60 * 1000 },
  { id: "6h", label: "6 hours", ms: 6 * 60 * 60 * 1000 },
  { id: "24h", label: "24 hours", ms: 24 * 60 * 60 * 1000 },
  { id: "7d", label: "7 days", ms: 7 * 24 * 60 * 60 * 1000 },
]

export const CASHFLOW_STATUSES = ["SUFFICIENT", "DEGRADED", "INSUFFICIENT", "UNKNOWN"]
export const REPAYMENT_STATUSES = [
  "CURRENT",
  "BEHIND_SCHEDULE",
  "DELINQUENT",
  "SEVERELY_UNPAID",
  "COMPLETED",
  "INSUFFICIENT_EVIDENCE",
  "UNKNOWN",
]

export const SNAPSHOT_ROOT_KEYS = [
  "schema_version",
  "purpose",
  "issued_at",
  "expires_at",
  "nonce_id",
  "assessment",
  "what_if",
]

export const ASSESSMENT_KEYS = [
  "borrower_alias",
  "evaluation_date",
  "readiness_index",
  "overall_confidence",
  "cashflow_status",
  "repayment_status",
  "new_credit_blocked",
  "monthly_surplus",
  "safe_emi_min",
  "safe_emi_max",
]

export const ENVELOPE_KEYS = [
  "version",
  "algorithm",
  "kdf",
  "kdf_parameters",
  "salt",
  "iv",
  "ciphertext",
  "content_type",
]

export const FORBIDDEN_SNAPSHOT_KEYS = [
  "transactions",
  "normalized_transactions",
  "account_number",
  "account_numbers",
  "upi_id",
  "upi_ids",
  "merchant_id",
  "merchant_ids",
  "merchant_name",
  "file",
  "files",
  "passphrase",
  "password",
  "key",
  "encryption_key",
  "lineage",
  "provenance",
  "sources",
  "informal_loans",
  "repayment_claims",
]

export const SHARE_FIELD_LABELS = {
  borrower_alias: "Borrower alias (only if you approve one)",
  evaluation_date: "Evaluation date",
  readiness_index: "Financial readiness summary",
  overall_confidence: "Overall confidence",
  cashflow_status: "Cash-flow status",
  repayment_status: "Repayment status",
  new_credit_blocked: "New-credit blocked flag",
  monthly_surplus: "Monthly surplus",
  safe_emi_min: "Safe EMI minimum",
  safe_emi_max: "Safe EMI maximum",
}

export const SHARE_EXCLUDED_LABELS = [
  "Raw borrower ID",
  "Bank transactions",
  "Account numbers",
  "UPI IDs",
  "Merchant names and IDs",
  "Uploaded files",
  "Raw provenance / lineage",
  "Encryption keys",
  "Passphrase",
]

/** Groups the user can include or omit. Labels come from SHARE_FIELD_LABELS. */
export const SHARE_GROUPS = [
  { id: "identity", fields: ["evaluation_date"], locked: true },
  { id: "readiness", fields: ["readiness_index", "overall_confidence"], locked: false },
  { id: "statuses", fields: ["cashflow_status", "repayment_status"], locked: false },
  { id: "blocked", fields: ["new_credit_blocked"], locked: false },
  { id: "surplus", fields: ["monthly_surplus"], locked: false },
  { id: "emi", fields: ["safe_emi_min", "safe_emi_max"], locked: false },
]
