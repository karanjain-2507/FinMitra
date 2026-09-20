import {
  ASSESSMENT_KEYS,
  CASHFLOW_STATUSES,
  FORBIDDEN_SNAPSHOT_KEYS,
  PURPOSE,
  REPAYMENT_STATUSES,
  SCHEMA_VERSION,
  SNAPSHOT_ROOT_KEYS,
} from "./constants.js"
import { INVALID_PURPOSE, INVALID_SNAPSHOT, ShareSecurityError } from "./errors.js"

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value)
}

function findForbiddenKey(value, path = "") {
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i += 1) {
      const hit = findForbiddenKey(value[i], `${path}[${i}]`)
      if (hit) return hit
    }
    return null
  }
  if (!isPlainObject(value)) return null
  for (const [key, child] of Object.entries(value)) {
    const here = path ? `${path}.${key}` : key
    if (FORBIDDEN_SNAPSHOT_KEYS.includes(key)) return here
    const hit = findForbiddenKey(child, here)
    if (hit) return hit
  }
  return null
}

function extraKeys(obj, allowed) {
  return Object.keys(obj).filter((key) => !allowed.includes(key))
}

function isIsoDateTime(value) {
  if (typeof value !== "string" || !value.endsWith("Z")) return false
  const parsed = Date.parse(value)
  return Number.isFinite(parsed)
}

function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value)
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

export function validateShareableSnapshot(snapshot) {
  assert(isPlainObject(snapshot), "Snapshot must be an object")
  const forbidden = findForbiddenKey(snapshot)
  if (forbidden) {
    throw new ShareSecurityError("FORBIDDEN_FIELD", INVALID_SNAPSHOT.message)
  }
  assert(extraKeys(snapshot, SNAPSHOT_ROOT_KEYS).length === 0, "Snapshot has unexpected fields")
  for (const key of SNAPSHOT_ROOT_KEYS) {
    assert(key in snapshot, `Missing snapshot field: ${key}`)
  }

  assert(snapshot.schema_version === SCHEMA_VERSION, "Unsupported snapshot schema")
  if (snapshot.purpose !== PURPOSE) {
    throw INVALID_PURPOSE
  }
  assert(isIsoDateTime(snapshot.issued_at), "issued_at must be UTC ISO-8601")
  assert(isIsoDateTime(snapshot.expires_at), "expires_at must be UTC ISO-8601")
  assert(Date.parse(snapshot.expires_at) > Date.parse(snapshot.issued_at), "expires_at must be after issued_at")
  assert(typeof snapshot.nonce_id === "string" && snapshot.nonce_id.length >= 16, "nonce_id is required")

  const assessment = snapshot.assessment
  assert(isPlainObject(assessment), "assessment must be an object")
  assert(extraKeys(assessment, ASSESSMENT_KEYS).length === 0, "assessment has unexpected fields")
  for (const key of ASSESSMENT_KEYS) {
    assert(key in assessment, `Missing assessment field: ${key}`)
  }

  assert(assessment.borrower_alias === null || (typeof assessment.borrower_alias === "string" && assessment.borrower_alias.length > 0), "invalid borrower_alias")
  assert(typeof assessment.evaluation_date === "string", "evaluation_date must be a string")
  assert(assessment.readiness_index === null || (isFiniteNumber(assessment.readiness_index) && assessment.readiness_index >= 0 && assessment.readiness_index <= 100), "invalid readiness_index")
  assert(assessment.overall_confidence === null || (isFiniteNumber(assessment.overall_confidence) && assessment.overall_confidence >= 0 && assessment.overall_confidence <= 1), "invalid overall_confidence")
  assert(assessment.cashflow_status === null || CASHFLOW_STATUSES.includes(assessment.cashflow_status), "invalid cashflow_status")
  assert(assessment.repayment_status === null || REPAYMENT_STATUSES.includes(assessment.repayment_status), "invalid repayment_status")
  assert(assessment.new_credit_blocked === null || typeof assessment.new_credit_blocked === "boolean", "invalid new_credit_blocked")
  assert(assessment.monthly_surplus === null || isFiniteNumber(assessment.monthly_surplus), "invalid monthly_surplus")
  assert(assessment.safe_emi_min === null || (isFiniteNumber(assessment.safe_emi_min) && assessment.safe_emi_min >= 0), "invalid safe_emi_min")
  assert(assessment.safe_emi_max === null || (isFiniteNumber(assessment.safe_emi_max) && assessment.safe_emi_max >= 0), "invalid safe_emi_max")

  assert(snapshot.what_if === null, "what_if must be null in this version")
  return true
}
