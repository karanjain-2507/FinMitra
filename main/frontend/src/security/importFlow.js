import { MAX_QR_CHARS } from "./constants.js"
import { decryptEnvelope } from "./crypto.js"
import { validateEnvelope } from "./envelope.js"
import { ENVELOPE_INVALID, OVERSIZED_PAYLOAD } from "./errors.js"

export function parseImportedPayload(raw) {
  if (typeof raw !== "string" || !raw.trim()) {
    throw ENVELOPE_INVALID
  }
  const text = raw.trim()
  if (text.length > MAX_QR_CHARS) {
    throw OVERSIZED_PAYLOAD
  }
  let parsed
  try {
    parsed = JSON.parse(text)
  } catch {
    throw ENVELOPE_INVALID
  }
  validateEnvelope(parsed)
  return parsed
}

export async function openImportedShare(raw, passphrase, options = {}) {
  const envelope = typeof raw === "string" ? parseImportedPayload(raw) : raw
  if (typeof raw !== "string") {
    validateEnvelope(envelope)
  }
  return decryptEnvelope(envelope, passphrase, options)
}
