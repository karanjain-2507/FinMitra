import jsQR from "jsqr"
import { ENVELOPE_INVALID, ShareSecurityError } from "./errors.js"

export const QR_NOT_FOUND = new ShareSecurityError(
  "QR_NOT_FOUND",
  "No QR code found. Try another image or paste the envelope JSON."
)

export function decodeQrFromImageData(imageData) {
  if (!imageData || !imageData.data) throw QR_NOT_FOUND
  const code = jsQR(imageData.data, imageData.width, imageData.height, {
    inversionAttempts: "attemptBoth",
  })
  if (!code?.data) throw QR_NOT_FOUND
  return code.data
}

export async function decodeQrFromImageFile(file) {
  if (!file) throw QR_NOT_FOUND
  const bitmap = await createImageBitmap(file)
  const canvas = document.createElement("canvas")
  canvas.width = bitmap.width
  canvas.height = bitmap.height
  const ctx = canvas.getContext("2d")
  ctx.drawImage(bitmap, 0, 0)
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
  bitmap.close?.()
  return decodeQrFromImageData(imageData)
}

export async function requestScanCamera() {
  if (!navigator?.mediaDevices?.getUserMedia) {
    throw new ShareSecurityError(
      "CAMERA_UNAVAILABLE",
      "Camera scanning is unavailable. Import a QR image or paste envelope JSON."
    )
  }
  return navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: "environment" } },
    audio: false,
  })
}

export function stopMediaStream(stream) {
  if (!stream) return
  for (const track of stream.getTracks()) track.stop()
}

export function scanVideoFrame(video) {
  if (!video || video.readyState < 2) return null
  const canvas = document.createElement("canvas")
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  if (!canvas.width || !canvas.height) return null
  const ctx = canvas.getContext("2d")
  ctx.drawImage(video, 0, 0)
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
  try {
    return decodeQrFromImageData(imageData)
  } catch {
    return null
  }
}

export function assertEnvelopeText(text) {
  if (typeof text !== "string" || !text.trim().startsWith("{")) {
    throw ENVELOPE_INVALID
  }
  return text
}
