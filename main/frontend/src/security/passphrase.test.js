import { describe, expect, it } from "vitest"
import { passphraseStrength } from "./passphrase.js"

describe("passphraseStrength", () => {
  it("labels short secrets as too short", () => {
    expect(passphraseStrength("abc").label).toBe("Too short")
  })

  it("rewards mixed case, numbers, and symbols", () => {
    expect(passphraseStrength("CorrectHorse1!").label).toBe("Very strong")
  })
})
