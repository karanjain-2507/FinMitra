import { describe, expect, it } from "vitest"
import { encryptSnapshot, decryptEnvelope } from "./crypto.js"
import { createShareableSnapshot } from "./snapshot.js"
import { GENERIC_DECRYPT_FAILURE, GENERIC_ENCRYPT_FAILURE, ENVELOPE_INVALID } from "./errors.js"
import { canonicalize } from "./canonicalize.js"
import { PBKDF2_ITERATIONS } from "./constants.js"

const now = new Date("2026-09-20T10:00:00.000Z")
const decryptNow = new Date("2026-09-20T12:00:00.000Z")
const passphrase = "correct-horse"
const result = {
  borrower_id: "B-1001",
  evaluation_date: "2026-09-19",
  profile: {
    readiness_index: 70,
    overall_confidence: 0.8,
    cashflow: { status: "DEGRADED" },
    repayment: { status: "BEHIND_SCHEDULE", new_credit_blocked: false },
    capacity: { baseline_monthly_surplus: 2500 },
    safe_emi: { minimum: 500, maximum: 1500 },
  },
}

function base64UrlToBytes(value) {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((value.length + 3) % 4)
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
  return bytes
}

function bytesToBase64Url(bytes) {
  let binary = ""
  bytes.forEach((b) => {
    binary += String.fromCharCode(b)
  })
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "")
}

function xorFirstByte(base64url) {
  const bytes = base64UrlToBytes(base64url)
  bytes[0] ^= 0x01
  return bytesToBase64Url(bytes)
}

describe("encryptSnapshot / decryptEnvelope", () => {
  it("round-trips a snapshot with the correct passphrase", async () => {
    const snapshot = createShareableSnapshot(result, { now, nonceId: "c".repeat(16), ttlMs: 86_400_000 })
    const envelope = await encryptSnapshot(snapshot, passphrase)
    expect(envelope.kdf_parameters.iterations).toBe(PBKDF2_ITERATIONS)
    expect(envelope.salt).not.toMatch(/[+/=]/)
    const opened = await decryptEnvelope(envelope, passphrase, { now: decryptNow })
    expect(canonicalize(opened)).toBe(canonicalize(snapshot))
  })

  it("decrypts a valid untouched ciphertext", async () => {
    const snapshot = createShareableSnapshot(result, { now, nonceId: "c2".repeat(8), ttlMs: 86_400_000 })
    const envelope = await encryptSnapshot(snapshot, passphrase)
    const opened = await decryptEnvelope({ ...envelope }, passphrase, { now: decryptNow })
    expect(opened.assessment.readiness_index).toBe(70)
    expect(opened).not.toBeNull()
  })

  it("uses a new IV and salt each time", async () => {
    const snapshot = createShareableSnapshot(result, { now, nonceId: "d".repeat(16) })
    const a = await encryptSnapshot(snapshot, passphrase)
    const b = await encryptSnapshot(snapshot, passphrase)
    expect(a.iv).not.toBe(b.iv)
    expect(a.salt).not.toBe(b.salt)
    expect(a.ciphertext).not.toBe(b.ciphertext)
  })

  it("fails generically on a wrong passphrase", async () => {
    const snapshot = createShareableSnapshot(result, { now, nonceId: "e".repeat(16) })
    const envelope = await encryptSnapshot(snapshot, passphrase)
    await expect(decryptEnvelope(envelope, "wrong-pass", { now: decryptNow })).rejects.toBe(GENERIC_DECRYPT_FAILURE)
  })

  it("fails authenticated decryption when one ciphertext byte is changed", async () => {
    const snapshot = createShareableSnapshot(result, { now, nonceId: "f".repeat(16), ttlMs: 86_400_000 })
    const envelope = await encryptSnapshot(snapshot, passphrase)
    const originalBytes = base64UrlToBytes(envelope.ciphertext)
    expect(originalBytes.byteLength).toBeGreaterThan(0)

    const tamperedBytes = new Uint8Array(originalBytes)
    tamperedBytes[0] ^= 0x01
    expect(tamperedBytes[0]).not.toBe(originalBytes[0])

    const tampered = { ...envelope, ciphertext: bytesToBase64Url(tamperedBytes) }
    expect(tampered.ciphertext).not.toBe(envelope.ciphertext)

    await expect(decryptEnvelope(tampered, passphrase, { now: decryptNow })).rejects.toBe(GENERIC_DECRYPT_FAILURE)
    await expect(decryptEnvelope(envelope, passphrase, { now: decryptNow })).resolves.toMatchObject({
      assessment: { readiness_index: 70 },
    })
  })

  it("fails generically when one IV byte is changed", async () => {
    const snapshot = createShareableSnapshot(result, { now, nonceId: "f1".repeat(8) })
    const envelope = await encryptSnapshot(snapshot, passphrase)
    const tampered = { ...envelope, iv: xorFirstByte(envelope.iv) }
    await expect(decryptEnvelope(tampered, passphrase, { now: decryptNow })).rejects.toBe(GENERIC_DECRYPT_FAILURE)
  })

  it("fails generically when one salt byte is changed", async () => {
    const snapshot = createShareableSnapshot(result, { now, nonceId: "f2".repeat(8) })
    const envelope = await encryptSnapshot(snapshot, passphrase)
    const tampered = { ...envelope, salt: xorFirstByte(envelope.salt) }
    await expect(decryptEnvelope(tampered, passphrase, { now: decryptNow })).rejects.toBe(GENERIC_DECRYPT_FAILURE)
  })

  it("rejects short passphrases on encrypt", async () => {
    const snapshot = createShareableSnapshot(result, { now, nonceId: "g".repeat(16) })
    await expect(encryptSnapshot(snapshot, "short")).rejects.toBe(GENERIC_ENCRYPT_FAILURE)
  })

  it("rejects a malformed envelope as ENVELOPE_INVALID, not a ReferenceError", async () => {
    await expect(decryptEnvelope(null, passphrase)).rejects.toBe(ENVELOPE_INVALID)
    await expect(decryptEnvelope("not-an-object", passphrase)).rejects.toBe(ENVELOPE_INVALID)
    await expect(decryptEnvelope({ version: "1" }, passphrase)).rejects.toBe(ENVELOPE_INVALID)
  })

  it("rejects an unsupported envelope version as ENVELOPE_INVALID", async () => {
    const snapshot = createShareableSnapshot(result, { now, nonceId: "h".repeat(16) })
    const envelope = await encryptSnapshot(snapshot, passphrase)
    await expect(decryptEnvelope({ ...envelope, version: "9" }, passphrase)).rejects.toBe(ENVELOPE_INVALID)
  })

  it("rejects an unsupported algorithm as ENVELOPE_INVALID", async () => {
    const snapshot = createShareableSnapshot(result, { now, nonceId: "i".repeat(16) })
    const envelope = await encryptSnapshot(snapshot, passphrase)
    await expect(decryptEnvelope({ ...envelope, algorithm: "AES-128-GCM" }, passphrase)).rejects.toBe(ENVELOPE_INVALID)
  })
})
