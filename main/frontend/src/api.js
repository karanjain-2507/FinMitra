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
