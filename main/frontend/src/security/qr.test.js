import { describe, expect, it } from "vitest"
import QRCode from "qrcode"
import {
  envelopeToQrPayload,
  parseEnvelopePayload,
  renderEnvelopeQrDataUrl,
  QrPayloadError,
} from "./qr.js"
import { encryptSnapshot } from "./crypto.js"
import { createShareableSnapshot } from "./snapshot.js"
import { OVERSIZED_PAYLOAD } from "./errors.js"
import { CONTENT_TYPE, ALGORITHM, ENVELOPE_VERSION, KDF, MAX_QR_CHARS, PBKDF2_ITERATIONS } from "./constants.js"

const distinctive = {
  readiness_index: 84.24681357,
  monthly_surplus: 12000.111,
  safe_emi_min: 4000.222,
  safe_emi_max: 8000.333,
}

const result = {
  borrower_id: "SHOP-998877",
  evaluation_date: "2026-09-19",
  profile: {
    ...distinctive,
    overall_confidence: 0.91,
    cashflow: { status: "SUFFICIENT" },
    repayment: { status: "COMPLETED", new_credit_blocked: false },
    capacity: { baseline_monthly_surplus: distinctive.monthly_surplus },
    safe_emi: { minimum: distinctive.safe_emi_min, maximum: distinctive.safe_emi_max },
  },
}

async function encryptedEnvelope() {
  const snapshot = createShareableSnapshot(result, {
    now: new Date("2026-09-20T10:00:00.000Z"),
    nonceId: "h".repeat(16),
    ttlMs: 86_400_000,
  })
  return {
    snapshot,
    passphrase: "never-in-the-qr",
    envelope: await encryptSnapshot(snapshot, "never-in-the-qr"),
  }
}

describe("qr payload", () => {
  it("generates a QR only after encryption and round-trips the envelope", async () => {
    const { envelope, passphrase, snapshot } = await encryptedEnvelope()
    const payload = envelopeToQrPayload(envelope)
    expect(payload.length).toBeLessThanOrEqual(MAX_QR_CHARS)
    expect(payload).not.toContain(passphrase)
    expect(payload).not.toContain(String(snapshot.assessment.readiness_index))
    expect(payload).not.toContain(String(snapshot.assessment.monthly_surplus))
    expect(payload).not.toContain("SHOP-998877")

    const dataUrl = await renderEnvelopeQrDataUrl(envelope)
    expect(dataUrl.startsWith("data:image/png")).toBe(true)

    const parsed = parseEnvelopePayload(payload)
    expect(parsed.ciphertext).toBe(envelope.ciphertext)

    const rebuilt = await QRCode.toString(payload, { type: "utf8", errorCorrectionLevel: "M" })
    expect(rebuilt.length).toBeGreaterThan(10)
  })

  it("rejects plaintext snapshots before QR generation", () => {
    const snapshot = createShareableSnapshot(result, {
      now: new Date("2026-09-20T10:00:00.000Z"),
      nonceId: "i".repeat(16),
    })
    expect(() => envelopeToQrPayload(snapshot)).toThrow(QrPayloadError)
  })

  it("rejects oversized payloads before QR generation", () => {
    const huge = {
      version: ENVELOPE_VERSION,
      algorithm: ALGORITHM,
      kdf: KDF,
      kdf_parameters: { iterations: PBKDF2_ITERATIONS },
      salt: "aaaaaaaaaaaaaaaaaaaaaa",
      iv: "bbbbbbbbbbbbbbbb",
      ciphertext: "c".repeat(MAX_QR_CHARS),
      content_type: CONTENT_TYPE,
    }
    expect(() => envelopeToQrPayload(huge)).toThrow(OVERSIZED_PAYLOAD)
  })
})
