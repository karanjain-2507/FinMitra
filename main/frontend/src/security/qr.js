import QRCode from "qrcode"
import { ENVELOPE_KEYS, MAX_QR_CHARS } from "./constants.js"
import { validateEnvelope } from "./envelope.js"

export class QrPayloadError extends Error {
  constructor(message) {
    super(message)
    this.name = "QrPayloadError"
  }
}

export function envelopeToQrPayload(envelope) {
  if (envelope && typeof envelope === "object" && ("assessment" in envelope || "schema_version" in envelope)) {
    throw new QrPayloadError("Plaintext snapshot cannot be placed in a QR")
  }
  validateEnvelope(envelope)
  const extra = Object.keys(envelope).filter((key) => !ENVELOPE_KEYS.includes(key))
  if (extra.length) {
    throw new QrPayloadError("QR payload must not contain plaintext financial fields")
  }
  const payload = JSON.stringify(envelope)
  if (payload.length > MAX_QR_CHARS) {
    throw new QrPayloadError("QR payload too large")
  }
  return payload
}

export async function renderEnvelopeQrDataUrl(envelope) {
  const payload = envelopeToQrPayload(envelope)
  return QRCode.toDataURL(payload, {
    errorCorrectionLevel: "M",
    margin: 4,
    width: 320,
    color: { dark: "#0B1F14", light: "#FFFFFF" },
  })
}

export function parseEnvelopePayload(text) {
  const parsed = JSON.parse(text)
  if (!parsed || typeof parsed !== "object") {
    throw new Error("invalid envelope")
  }
  validateEnvelope(parsed)
  return parsed
}
