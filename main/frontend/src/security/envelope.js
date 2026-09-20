import {
  ALGORITHM,
  CONTENT_TYPE,
  ENVELOPE_KEYS,
  ENVELOPE_VERSION,
  KDF,
  MAX_QR_CHARS,
  PBKDF2_ITERATIONS,
} from "./constants.js"
import { ENVELOPE_INVALID, OVERSIZED_PAYLOAD } from "./errors.js"

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value)
}

function extraKeys(obj, allowed) {
  return Object.keys(obj).filter((key) => !allowed.includes(key))
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

export function validateEnvelope(envelope) {
  try {
    assert(isPlainObject(envelope), "Envelope must be an object")
    assert(extraKeys(envelope, ENVELOPE_KEYS).length === 0, "Envelope has unexpected fields")
    for (const key of ENVELOPE_KEYS) {
      assert(key in envelope, `Missing envelope field: ${key}`)
    }
    assert(envelope.version === ENVELOPE_VERSION, "Unsupported envelope version")
    assert(envelope.algorithm === ALGORITHM, "Unsupported algorithm")
    assert(envelope.kdf === KDF, "Unsupported KDF")
    assert(isPlainObject(envelope.kdf_parameters), "kdf_parameters must be an object")
    assert(envelope.kdf_parameters.iterations === PBKDF2_ITERATIONS, "Unsupported iteration count")
    assert(typeof envelope.salt === "string" && envelope.salt.length > 0, "salt is required")
    assert(typeof envelope.iv === "string" && envelope.iv.length > 0, "iv is required")
    assert(typeof envelope.ciphertext === "string" && envelope.ciphertext.length > 0, "ciphertext is required")
    assert(envelope.content_type === CONTENT_TYPE, "Unsupported content type")
    const serialized = JSON.stringify(envelope)
    if (serialized.length > MAX_QR_CHARS) throw OVERSIZED_PAYLOAD
    return true
  } catch (error) {
    if (error === OVERSIZED_PAYLOAD) throw error
    throw ENVELOPE_INVALID
  }
}
