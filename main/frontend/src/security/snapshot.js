import {
  DEFAULT_TTL_MS,
  PURPOSE,
  SCHEMA_VERSION,
  SHARE_FIELD_LABELS,
  SHARE_GROUPS,
} from "./constants.js"
import { validateShareableSnapshot } from "./snapshotSchema.js"

function toIsoUtc(date) {
  return new Date(date).toISOString().replace(/\.\d{3}Z$/, "Z")
}

function bytesToHex(bytes) {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("")
}

function randomNonceId() {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return bytesToHex(bytes)
}

function pickString(...candidates) {
  for (const value of candidates) {
    if (typeof value === "string" && value.trim()) return value
  }
  return null
}

function asNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function asBoolean(value) {
  return typeof value === "boolean" ? value : null
}

/** Only an explicit user-approved alias. Never derived from borrower_id. */
function userApprovedAlias(candidate, result, profile) {
  if (typeof candidate !== "string") return null
  const alias = candidate.trim()
  if (!alias) return null
  const blocked = [
    result?.borrower_id,
    profile?.borrower_id,
    result?.account_number,
    profile?.account_number,
    result?.upi_id,
    profile?.upi_id,
  ]
  for (const value of blocked) {
    if (typeof value === "string" && value.trim() && alias === value.trim()) return null
  }
  return alias
}

function nested(result) {
  return result?.profile && typeof result.profile === "object" ? result.profile : result
}

/**
 * Build an allowlisted snapshot from an assessment result.
 * Raw borrower_id is never copied. Alias is included only if user-approved.
 */
export function createShareableSnapshot(result, options = {}) {
  if (!result || typeof result !== "object") {
    throw new Error("Assessment result is required")
  }

  const profile = nested(result)
  const cashflow = profile.cashflow && typeof profile.cashflow === "object" ? profile.cashflow : {}
  const repayment = profile.repayment && typeof profile.repayment === "object" ? profile.repayment : {}
  const capacity = profile.capacity && typeof profile.capacity === "object" ? profile.capacity : {}
  const safeEmi = profile.safe_emi && typeof profile.safe_emi === "object" ? profile.safe_emi : {}

  const now = options.now instanceof Date ? options.now : new Date()
  const ttlMs = Number.isFinite(options.ttlMs) ? options.ttlMs : DEFAULT_TTL_MS
  const issuedAt = toIsoUtc(now)
  const expiresAt = toIsoUtc(new Date(now.getTime() + ttlMs))
  if (Date.parse(expiresAt) <= Date.parse(issuedAt)) {
    throw new Error("expires_at must be after issued_at")
  }

  const snapshot = {
    schema_version: SCHEMA_VERSION,
    purpose: PURPOSE,
    issued_at: issuedAt,
    expires_at: expiresAt,
    nonce_id: options.nonceId || randomNonceId(),
    assessment: {
      borrower_alias: userApprovedAlias(options.borrowerAlias, result, profile),
      evaluation_date: pickString(result.evaluation_date, profile.evaluation_date) || issuedAt.slice(0, 10),
      readiness_index: asNumber(profile.readiness_index),
      overall_confidence: asNumber(profile.overall_confidence),
      cashflow_status: pickString(cashflow.status, profile.cashflow_status),
      repayment_status: pickString(repayment.status, profile.repayment_status),
      new_credit_blocked: asBoolean(repayment.new_credit_blocked) ?? asBoolean(profile.new_credit_blocked),
      monthly_surplus: asNumber(capacity.baseline_monthly_surplus) ?? asNumber(profile.monthly_surplus),
      safe_emi_min: asNumber(safeEmi.minimum) ?? asNumber(profile.safe_emi_min),
      safe_emi_max: asNumber(safeEmi.maximum) ?? asNumber(profile.safe_emi_max),
    },
    what_if: null,
  }

  validateShareableSnapshot(snapshot)
  return applyShareSelection(snapshot, options.selectedGroups)
}

export function defaultSelectedGroups() {
  return SHARE_GROUPS.map((group) => group.id)
}

export function applyShareSelection(snapshot, selectedGroups) {
  const selected = new Set(selectedGroups?.length ? selectedGroups : defaultSelectedGroups())
  const next = {
    ...snapshot,
    assessment: { ...snapshot.assessment },
  }
  for (const group of SHARE_GROUPS) {
    if (group.locked) continue
    if (selected.has(group.id)) continue
    for (const field of group.fields) {
      next.assessment[field] = null
    }
  }
  validateShareableSnapshot(next)
  return next
}

/** Preview rows from the actual allowlisted snapshot, not a parallel label list. */
export function snapshotPreviewRows(snapshot) {
  validateShareableSnapshot(snapshot)
  return Object.keys(snapshot.assessment).map((key) => ({
    key,
    label: SHARE_FIELD_LABELS[key] || key,
    value: snapshot.assessment[key],
    included: snapshot.assessment[key] !== null,
  }))
}
