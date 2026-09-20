import { describe, expect, it } from "vitest"
import { validateShareableSnapshot } from "./snapshotSchema.js"
import { PURPOSE, SCHEMA_VERSION } from "./constants.js"

function validSnapshot(overrides = {}) {
  return {
    schema_version: SCHEMA_VERSION,
    purpose: PURPOSE,
    issued_at: "2026-09-20T10:00:00Z",
    expires_at: "2026-09-21T10:00:00Z",
    nonce_id: "0123456789abcdef",
    assessment: {
      borrower_alias: "Borrower-8877",
      evaluation_date: "2026-09-19",
      readiness_index: 84,
      overall_confidence: 0.9,
      cashflow_status: "SUFFICIENT",
      repayment_status: "CURRENT",
      new_credit_blocked: false,
      monthly_surplus: 1000,
      safe_emi_min: 400,
      safe_emi_max: 800,
    },
    what_if: null,
    ...overrides,
  }
}

describe("validateShareableSnapshot", () => {
  it("accepts a complete allowlisted snapshot", () => {
    expect(validateShareableSnapshot(validSnapshot())).toBe(true)
  })

  it("rejects extra and forbidden fields", () => {
    expect(() => validateShareableSnapshot(validSnapshot({ extra: 1 }))).toThrow()
    expect(() =>
      validateShareableSnapshot({
        ...validSnapshot(),
        assessment: { ...validSnapshot().assessment, transactions: [] },
      })
    ).toThrow()
  })

  it("rejects what_if payloads in this version", () => {
    expect(() => validateShareableSnapshot(validSnapshot({ what_if: { amount: 1 } }))).toThrow()
  })

  it("accepts legitimately unavailable financial fields as null", () => {
    expect(
      validateShareableSnapshot({
        ...validSnapshot(),
        assessment: {
          ...validSnapshot().assessment,
          borrower_alias: null,
          readiness_index: null,
          overall_confidence: null,
          new_credit_blocked: null,
          monthly_surplus: null,
          safe_emi_min: null,
          safe_emi_max: null,
          cashflow_status: null,
          repayment_status: null,
        },
      })
    ).toBe(true)
  })
})
