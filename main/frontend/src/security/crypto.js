import {
  ALGORITHM,
  CONTENT_TYPE,
  ENVELOPE_VERSION,
  IV_BYTES,
  KDF,
  KEY_BITS,
  MAX_PLAINTEXT_BYTES,
  PBKDF2_ITERATIONS,
  SALT_BYTES,
} from "./constants.js"
import { canonicalize } from "./canonicalize.js"
import { validateEnvelope } from "./envelope.js"
import {
  GENERIC_DECRYPT_FAILURE,
  GENERIC_ENCRYPT_FAILURE,
  INVALID_PURPOSE,
  INVALID_SNAPSHOT,
  SHARE_EXPIRED,
  ENVELOPE_INVALID,
  ShareSecurityError,
} from "./errors.js"
import { validateShareableSnapshot } from "./snapshotSchema.js"

const encoder = new TextEncoder()
const decoder = new TextDecoder()

function bytesToBase64Url(bytes) {
  let binary = ""
  bytes.forEach((b) => {
    binary += String.fromCharCode(b)
  })
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "")
}

function base64UrlToBytes(value) {
  if (typeof value !== "string" || !value) throw new Error("invalid base64")
  const padded = value.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((value.length + 3) % 4)
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
  return bytes
}

function randomBytes(length) {
  const bytes = new Uint8Array(length)
  crypto.getRandomValues(bytes)
  return bytes
}

async function deriveKey(passphrase, salt) {
  const material = await crypto.subtle.importKey(
    "raw",
    encoder.encode(passphrase),
    "PBKDF2",
    false,
    ["deriveKey"]
  )
  return crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt,
      iterations: PBKDF2_ITERATIONS,
      hash: "SHA-256",
    },
    material,
    { name: "AES-GCM", length: KEY_BITS },
    false,
    ["encrypt", "decrypt"]
  )
}

function utf8ByteLength(text) {
  return encoder.encode(text).byteLength
}

export async function encryptSnapshot(snapshot, passphrase) {
  try {
    if (typeof passphrase !== "string" || passphrase.length < 8) {
      throw GENERIC_ENCRYPT_FAILURE
    }
    validateShareableSnapshot(snapshot)
    if (Date.parse(snapshot.expires_at) <= Date.now()) {
      throw GENERIC_ENCRYPT_FAILURE
    }
    const plaintext = canonicalize(snapshot)
    if (utf8ByteLength(plaintext) > MAX_PLAINTEXT_BYTES) {
      throw GENERIC_ENCRYPT_FAILURE
    }

    const salt = randomBytes(SALT_BYTES)
    const iv = randomBytes(IV_BYTES)
    const key = await deriveKey(passphrase, salt)
    const ciphertext = new Uint8Array(
      await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, encoder.encode(plaintext))
    )

    const envelope = {
      version: ENVELOPE_VERSION,
      algorithm: ALGORITHM,
      kdf: KDF,
      kdf_parameters: { iterations: PBKDF2_ITERATIONS },
      salt: bytesToBase64Url(salt),
      iv: bytesToBase64Url(iv),
      ciphertext: bytesToBase64Url(ciphertext),
      content_type: CONTENT_TYPE,
    }
    validateEnvelope(envelope)
    return envelope
  } catch (error) {
    if (error === GENERIC_ENCRYPT_FAILURE) throw error
    throw GENERIC_ENCRYPT_FAILURE
  }
}

export async function encryptUtf8Plaintext(plaintext, passphrase) {
  if (typeof passphrase !== "string" || passphrase.length < 8) {
    throw GENERIC_ENCRYPT_FAILURE
  }
  if (typeof plaintext !== "string") throw GENERIC_ENCRYPT_FAILURE
  if (utf8ByteLength(plaintext) > MAX_PLAINTEXT_BYTES) throw GENERIC_ENCRYPT_FAILURE
  const salt = randomBytes(SALT_BYTES)
  const iv = randomBytes(IV_BYTES)
  const key = await deriveKey(passphrase, salt)
  const ciphertext = new Uint8Array(
    await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, encoder.encode(plaintext))
  )
  const envelope = {
    version: ENVELOPE_VERSION,
    algorithm: ALGORITHM,
    kdf: KDF,
    kdf_parameters: { iterations: PBKDF2_ITERATIONS },
    salt: bytesToBase64Url(salt),
    iv: bytesToBase64Url(iv),
    ciphertext: bytesToBase64Url(ciphertext),
    content_type: CONTENT_TYPE,
  }
  validateEnvelope(envelope)
  return envelope
}

export async function decryptEnvelope(envelope, passphrase, options = {}) {
  try {
    validateEnvelope(envelope)
  } catch (error) {
    if (error instanceof ShareSecurityError) throw error
    throw ENVELOPE_INVALID
  }

  let parsed
  try {
    if (typeof passphrase !== "string" || !passphrase) {
      throw GENERIC_DECRYPT_FAILURE
    }
    const salt = base64UrlToBytes(envelope.salt)
    const iv = base64UrlToBytes(envelope.iv)
    const ciphertext = base64UrlToBytes(envelope.ciphertext)
    if (salt.byteLength !== SALT_BYTES || iv.byteLength !== IV_BYTES) {
      throw ENVELOPE_INVALID
    }
    const key = await deriveKey(passphrase, salt)
    const plaintextBytes = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv },
      key,
      ciphertext
    )
    parsed = JSON.parse(decoder.decode(plaintextBytes))
  } catch (error) {
    if (error === GENERIC_DECRYPT_FAILURE) throw error
    if (error instanceof ShareSecurityError && error.code === "ENVELOPE_INVALID") throw ENVELOPE_INVALID
    throw GENERIC_DECRYPT_FAILURE
  }

  try {
    validateShareableSnapshot(parsed)
  } catch (error) {
    if (error === INVALID_PURPOSE || error?.code === "INVALID_PURPOSE") throw INVALID_PURPOSE
    if (error?.code === "FORBIDDEN_FIELD") throw error
    throw INVALID_SNAPSHOT
  }

  const clock = options.now instanceof Date ? options.now : new Date()
  if (Date.parse(parsed.expires_at) <= clock.getTime()) {
    throw SHARE_EXPIRED
  }
  return parsed
}
