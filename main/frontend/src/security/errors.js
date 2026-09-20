export class ShareSecurityError extends Error {
  constructor(code, userMessage) {
    super(userMessage)
    this.name = "ShareSecurityError"
    this.code = code
  }
}

export const GENERIC_DECRYPT_MESSAGE =
  "Unable to open this secure FinMitra share. Check the passphrase or QR data."

export const UNSUPPORTED_SHARE_MESSAGE = "This QR is not a supported FinMitra share."

export const GENERIC_DECRYPT_FAILURE = new ShareSecurityError("DECRYPT_FAILED", GENERIC_DECRYPT_MESSAGE)

export const GENERIC_ENCRYPT_FAILURE = new ShareSecurityError(
  "ENCRYPT_FAILED",
  "Unable to create a secure share. Try again with a new passphrase."
)

export const ENVELOPE_INVALID = new ShareSecurityError("ENVELOPE_INVALID", UNSUPPORTED_SHARE_MESSAGE)

export const OVERSIZED_PAYLOAD = new ShareSecurityError("OVERSIZED_PAYLOAD", UNSUPPORTED_SHARE_MESSAGE)

export const SHARE_EXPIRED = new ShareSecurityError(
  "SHARE_EXPIRED",
  "This FinMitra share has expired."
)

export const INVALID_PURPOSE = new ShareSecurityError("INVALID_PURPOSE", UNSUPPORTED_SHARE_MESSAGE)

export const INVALID_SNAPSHOT = new ShareSecurityError("INVALID_SNAPSHOT", UNSUPPORTED_SHARE_MESSAGE)

export function userMessageForShareError(error) {
  if (error instanceof ShareSecurityError) return error.message
  return GENERIC_DECRYPT_MESSAGE
}
