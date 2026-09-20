const BASE = '/api'

async function _fetch(url, options = {}) {
  const res = await fetch(BASE + url, options)
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try { detail = (await res.json()).detail ?? detail } catch { /* ignore */ }
    throw new Error(detail)
  }
  return res.json()
}

/** Run one of the three bundled demo scenarios. */
export function runDemo(scenario) {
  return _fetch(`/demo/${scenario}`)
}

/** Upload a CSV + form fields and run the pipeline. */
export function assessCsv(formData) {
  return _fetch('/assess/csv', { method: 'POST', body: formData })
}

/** POST a full IntegratedBorrowerInput JSON object. */
export function assessJson(payload) {
  return _fetch('/assess', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

/** Plan from an immutable assessment snapshot held by the server. */
export function planAssessment(assessmentId, goal) {
  return _fetch('/what-if', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assessment_id: assessmentId, goal }),
  })
}

/** Plan a goal from one of the server-owned demo assessments. */
export function planDemo(scenario, goal) {
  return _fetch(`/what-if/demo/${scenario}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(goal),
  })
}

/** Reassess an uploaded statement and plan from the authoritative result. */
export function planCsv(file, context, goal) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('goal', JSON.stringify(goal))
  formData.append('borrower_id', context.borrowerId || 'BORROWER-001')
  formData.append('business_name', context.businessName || '')
  formData.append('evaluation_date', context.evaluationDate)
  formData.append('source_type', context.sourceType || 'BANK_STATEMENT')
  formData.append('household_expense', context.householdExpense ?? 0)
  formData.append('balance_buffer', context.balanceBuffer ?? 0)
  return _fetch('/what-if/csv', { method: 'POST', body: formData })
}

/** Issue a privacy-preserving passport from a server-owned assessment. */
export function issuePassport(assessmentId, goal = null) {
  return _fetch('/passports', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assessment_id: assessmentId, goal }),
  })
}

/** Verify a passport ID against its signed credential. */
export function verifyPassport(credentialId) {
  return _fetch('/passports/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ credential_id: credentialId }),
  })
}
