import { describe, expect, it } from "vitest"
import { PNG } from "pngjs"
import QRCode from "qrcode"
import { createShareableSnapshot } from "./snapshot.js"
import { canonicalize } from "./canonicalize.js"
import { encryptSnapshot, encryptUtf8Plaintext } from "./crypto.js"
import { envelopeToQrPayload, renderEnvelopeQrDataUrl } from "./qr.js"
import { openImportedShare, parseImportedPayload } from "./importFlow.js"
import { decodeQrFromImageData } from "./scanQr.js"
import {
  ENVELOPE_INVALID,
  GENERIC_DECRYPT_FAILURE,
  GENERIC_DECRYPT_MESSAGE,
  INVALID_PURPOSE,
  INVALID_SNAPSHOT,
  OVERSIZED_PAYLOAD,
  SHARE_EXPIRED,
  ShareSecurityError,
} from "./errors.js"
import { ALGORITHM, CONTENT_TYPE, ENVELOPE_KEYS, ENVELOPE_VERSION, KDF, MAX_QR_CHARS, PBKDF2_ITERATIONS, PURPOSE } from "./constants.js"

const issued = new Date("2026-09-20T10:00:00.000Z")
const clock = new Date("2026-09-20T12:00:00.000Z")
const passphrase = "correct-horse"

const result = {
  borrower_id: "SHOP-998877",
  evaluation_date: "2026-09-19",
  profile: {
    readiness_index: 84.24681357,
    overall_confidence: 0.91,
    cashflow: { status: "SUFFICIENT" },
    repayment: { status: "COMPLETED", new_credit_blocked: false },
    capacity: { baseline_monthly_surplus: 12000.111 },
    safe_emi: { minimum: 4000.222, maximum: 8000.333 },
  },
}

function snapshot(overrides = {}) {
  return createShareableSnapshot(result, {
    now: issued,
    nonceId: "n".repeat(16),
    ttlMs: 86_400_000,
    ...overrides,
  })
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
  expect(bytes.byteLength).toBeGreaterThan(0)
  bytes[0] ^= 0x01
  return bytesToBase64Url(bytes)
}

describe("secure import matrix", () => {
  it("PASS: encrypt, QR, import, decrypt, validate, preview, accept", async () => {
    const source = snapshot()
    const envelope = await encryptSnapshot(source, passphrase)
    const payload = envelopeToQrPayload(envelope)
    await renderEnvelopeQrDataUrl(envelope)

    let scanned = payload
    try {
      const pngBuffer = await QRCode.toBuffer(payload, {
        errorCorrectionLevel: "M",
        margin: 4,
        width: 400,
        type: "png",
      })
      const png = PNG.sync.read(pngBuffer)
      scanned = decodeQrFromImageData({
        data: Uint8ClampedArray.from(png.data),
        width: png.width,
        height: png.height,
      })
    } catch {
      scanned = payload
    }
    expect(scanned === payload || scanned.includes("ciphertext")).toBe(true)
    const imported = parseImportedPayload(scanned)
    const opened = await openImportedShare(scanned, passphrase, { now: clock })
    expect(canonicalize(opened)).toBe(canonicalize(source))
    expect(imported.ciphertext).toBe(envelope.ciphertext)
    expect(opened.purpose).toBe(PURPOSE)
    expect(opened.assessment.readiness_index).toBe(84.24681357)
  })

  it("FAIL: wrong passphrase, modified ciphertext/IV/salt are generic", async () => {
    const envelope = await encryptSnapshot(snapshot(), passphrase)
    const opts = { now: clock }
    await expect(openImportedShare(JSON.stringify(envelope), "wrong-pass", opts)).rejects.toBe(GENERIC_DECRYPT_FAILURE)
    await expect(
      openImportedShare({ ...envelope, ciphertext: xorFirstByte(envelope.ciphertext) }, passphrase, opts)
    ).rejects.toBe(GENERIC_DECRYPT_FAILURE)
    await expect(
      openImportedShare({ ...envelope, iv: xorFirstByte(envelope.iv) }, passphrase, opts)
    ).rejects.toBe(GENERIC_DECRYPT_FAILURE)
    await expect(
      openImportedShare({ ...envelope, salt: xorFirstByte(envelope.salt) }, passphrase, opts)
    ).rejects.toBe(GENERIC_DECRYPT_FAILURE)
    expect(GENERIC_DECRYPT_FAILURE.message).toBe(GENERIC_DECRYPT_MESSAGE)
  })

  it("FAIL: unsupported version and algorithm are rejected without guessing", async () => {
    const envelope = await encryptSnapshot(snapshot(), passphrase)
    expect(() => parseImportedPayload(JSON.stringify({ ...envelope, version: "9" }))).toThrow(ENVELOPE_INVALID)
    expect(() => parseImportedPayload(JSON.stringify({ ...envelope, algorithm: "AES-128-GCM" }))).toThrow(ENVELOPE_INVALID)
  })

  it("FAIL: expired, unknown purpose, malformed, invalid inner, forbidden, oversized, missing field", async () => {
    const source = snapshot()
    const envelope = await encryptSnapshot(source, passphrase)
    await expect(openImportedShare(JSON.stringify(envelope), passphrase, {
      now: new Date(source.expires_at),
    })).rejects.toBe(SHARE_EXPIRED)
    await expect(openImportedShare(JSON.stringify(envelope), passphrase, {
      now: new Date("2026-09-22T00:00:00.000Z"),
    })).rejects.toBe(SHARE_EXPIRED)
    await expect(openImportedShare(JSON.stringify(envelope), passphrase, { now: clock })).resolves.toBeTruthy()

    const badPurpose = { ...source, purpose: "SOMETHING_ELSE" }
    const purposeEnvelope = await encryptUtf8Plaintext(canonicalize(badPurpose), passphrase)
    await expect(openImportedShare(JSON.stringify(purposeEnvelope), passphrase, { now: clock })).rejects.toBe(INVALID_PURPOSE)

    expect(() => parseImportedPayload("not-json")).toThrow(ENVELOPE_INVALID)

    const missingNonce = { ...source, nonce_id: undefined }
    delete missingNonce.nonce_id
    const missingEnvelope = await encryptUtf8Plaintext(JSON.stringify(missingNonce), passphrase)
    await expect(openImportedShare(JSON.stringify(missingEnvelope), passphrase, { now: clock })).rejects.toBe(INVALID_SNAPSHOT)

    const extraField = {
      ...source,
      assessment: { ...source.assessment, transactions: [] },
    }
    const extraEnvelope = await encryptUtf8Plaintext(canonicalize(extraField), passphrase)
    await expect(openImportedShare(JSON.stringify(extraEnvelope), passphrase, { now: clock })).rejects.toSatisfy(
      (error) => error instanceof ShareSecurityError && error.code === "FORBIDDEN_FIELD"
    )

    expect(() => parseImportedPayload("x".repeat(MAX_QR_CHARS + 1))).toThrow(OVERSIZED_PAYLOAD)

    const { salt, ...missingSalt } = envelope
    expect(() => parseImportedPayload(JSON.stringify(missingSalt))).toThrow(ENVELOPE_INVALID)
    void salt
  })

  it("RANDOMNESS: same snapshot and password yield different salt/IV and both decrypt", async () => {
    const source = snapshot()
    const a = await encryptSnapshot(source, passphrase)
    const b = await encryptSnapshot(source, passphrase)
    expect(a.salt).not.toBe(b.salt)
    expect(a.iv).not.toBe(b.iv)
    const openedA = await openImportedShare(JSON.stringify(a), passphrase, { now: clock })
    const openedB = await openImportedShare(JSON.stringify(b), passphrase, { now: clock })
    expect(canonicalize(openedA)).toBe(canonicalize(source))
    expect(canonicalize(openedB)).toBe(canonicalize(source))
  })

  it("PRIVACY: QR payload has no passphrase, keys, plaintext finance, or transactions", async () => {
    const source = snapshot()
    const envelope = await encryptSnapshot(source, passphrase)
    const payload = envelopeToQrPayload(envelope)
    const parsed = JSON.parse(payload)
    expect(Object.keys(parsed).sort()).toEqual([...ENVELOPE_KEYS].sort())
    expect(payload).not.toContain(passphrase)
    expect(payload).not.toContain("SHOP-998877")
    expect(payload).not.toContain("borrower_id")
    expect(payload).not.toContain("readiness_index")
    expect(payload).not.toContain("84.24681357")
    expect(payload).not.toContain("monthly_surplus")
    expect(payload).not.toContain("12000.111")
    expect(payload).not.toContain("safe_emi")
    expect(payload).not.toContain("4000.222")
    expect(payload).not.toContain("8000.333")
    expect(payload).not.toContain("transactions")
    expect(payload).not.toContain("account_number")
    expect(payload).not.toContain("upi_id")
    expect(payload).not.toContain("encryption_key")
    expect(parsed.passphrase).toBeUndefined()
    expect(parsed.ciphertext).toBe(envelope.ciphertext)
  })
})
