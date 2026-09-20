/** Deterministic JSON for encryption. Nested keys are sorted. */

function sortValue(value) {
  if (Array.isArray(value)) {
    return value.map(sortValue)
  }
  if (value && typeof value === "object") {
    const out = {}
    for (const key of Object.keys(value).sort()) {
      out[key] = sortValue(value[key])
    }
    return out
  }
  return value
}

export function canonicalize(value) {
  return JSON.stringify(sortValue(value))
}
