import { describe, expect, it } from "vitest"
import { createShareableSnapshot, snapshotPreviewRows } from "./snapshot.js"
import { FORBIDDEN_SNAPSHOT_KEYS, SHARE_FIELD_LABELS } from "./constants.js"
import { validateShareableSnapshot } from "./snapshotSchema.js"

const now = new Date("2026-09-20T10:00:00.000Z")

const pipelineResult = {
  borrower_id: "SHOP-998877",
  evaluation_date: "2026-09-19",
  profile: {
    readiness_index: 84.2,
    overall_confidence: 0.91,
    cashflow: { status: "SUFFICIENT", stress_probability: 0.12 },
    repayment: { status: "COMPLETED", new_credit_blocked: false },
    capacity: { baseline_monthly_surplus: 12000 },
    safe_emi: { minimum: 4000, maximum: 8000 },
    evidence: { evidence_grade: "A" },
  },
  lineage: { source_count: 3, raw_transaction_count: 120 },
}

describe("createShareableSnapshot", () => {
  it("maps allowlisted fields without exposing borrower_id", () => {
    const snapshot = createShareableSnapshot(pipelineResult, { now, ttlMs: 3600000, nonceId: "a".repeat(16) })
    expect(validateShareableSnapshot(snapshot)).toBe(true)
    expect(snapshot.assessment.borrower_alias).toBeNull()
    expect(JSON.stringify(snapshot)).not.toContain("SHOP-998877")
    expect(JSON.stringify(snapshot)).not.toContain("Borrower-8877")
    expect(snapshot.assessment.cashflow_status).toBe("SUFFICIENT")
    expect(snapshot.assessment.repayment_status).toBe("COMPLETED")
    expect(snapshot.assessment.safe_emi_min).toBe(4000)
    expect(snapshot.assessment.readiness_index).toBe(84.2)
    expect(snapshot.assessment.overall_confidence).toBe(0.91)
    expect(snapshot.assessment.new_credit_blocked).toBe(false)
    expect(snapshot.what_if).toBeNull()
  })

  it("preserves actual zero and false instead of treating them as missing", () => {
    const snapshot = createShareableSnapshot({
      borrower_id: "B-0",
      evaluation_date: "2026-09-19",
      profile: {
        readiness_index: 0,
        overall_confidence: 0,
        cashflow: { status: "INSUFFICIENT" },
        repayment: { status: "CURRENT", new_credit_blocked: false },
        capacity: { baseline_monthly_surplus: 0 },
        safe_emi: { minimum: 0, maximum: 0 },
      },
    }, { now, nonceId: "z".repeat(16) })
    expect(snapshot.assessment.readiness_index).toBe(0)
    expect(snapshot.assessment.overall_confidence).toBe(0)
    expect(snapshot.assessment.new_credit_blocked).toBe(false)
    expect(snapshot.assessment.monthly_surplus).toBe(0)
    expect(snapshot.assessment.safe_emi_min).toBe(0)
  })

  it("keeps missing readiness_index, overall_confidence, and new_credit_blocked as null", () => {
    const snapshot = createShareableSnapshot({
      borrower_id: "B-THIN",
      evaluation_date: "2026-09-19",
      profile: {
        cashflow: {},
        repayment: {},
        capacity: {},
        safe_emi: {},
      },
    }, { now, nonceId: "m".repeat(16) })
    expect(validateShareableSnapshot(snapshot)).toBe(true)
    expect(snapshot.assessment.readiness_index).toBeNull()
    expect(snapshot.assessment.overall_confidence).toBeNull()
    expect(snapshot.assessment.new_credit_blocked).toBeNull()
    expect(snapshot.assessment.monthly_surplus).toBeNull()
    expect(snapshot.assessment.safe_emi_min).toBeNull()
    expect(snapshot.assessment.safe_emi_max).toBeNull()
    expect(snapshot.assessment.cashflow_status).toBeNull()
    expect(snapshot.assessment.repayment_status).toBeNull()
    expect(snapshot.assessment.readiness_index).not.toBe(0)
    expect(snapshot.assessment.new_credit_blocked).not.toBe(false)
  })

  it("omits forbidden keys from the snapshot", () => {
    const snapshot = createShareableSnapshot(pipelineResult, { now, nonceId: "b".repeat(16) })
    const blob = JSON.stringify(snapshot)
    for (const key of ["transactions", "account_number", "upi_id", "passphrase", "lineage"]) {
      expect(blob.includes(`"${key}"`)).toBe(false)
    }
    expect(FORBIDDEN_SNAPSHOT_KEYS.some((key) => key in snapshot)).toBe(false)
  })

  it("builds preview rows from the snapshot and can omit selected groups", () => {
    const snapshot = createShareableSnapshot(pipelineResult, {
      now,
      nonceId: "c".repeat(16),
      selectedGroups: ["identity", "statuses"],
    })
    const rows = snapshotPreviewRows(snapshot)
    expect(rows.map((row) => row.label)).toEqual(Object.keys(snapshot.assessment).map((key) => SHARE_FIELD_LABELS[key]))
    expect(snapshot.assessment.readiness_index).toBeNull()
    expect(snapshot.assessment.safe_emi_min).toBeNull()
    expect(snapshot.assessment.cashflow_status).toBe("SUFFICIENT")
    expect(snapshot.assessment.borrower_alias).toBeNull()
  })

  it("never includes borrower_id or auto-generated aliases", () => {
    const snapshot = createShareableSnapshot(pipelineResult, { now, nonceId: "p1".repeat(8) })
    const blob = JSON.stringify(snapshot)
    expect(blob).not.toContain("borrower_id")
    expect(blob).not.toContain("SHOP-998877")
    expect(blob).not.toContain("Borrower-8877")
    expect(blob).not.toMatch(/Borrower-\d+/)
    expect(snapshot.assessment.borrower_alias).toBeNull()
    const preview = snapshotPreviewRows(snapshot).find((row) => row.key === "borrower_alias")
    expect(preview.included).toBe(false)
    expect(preview.value).toBeNull()
  })

  it("does not expose identity when no user-approved alias is provided", () => {
    const snapshot = createShareableSnapshot({
      ...pipelineResult,
      account_number: "123456789012",
      upi_id: "shop@upi",
      profile: {
        ...pipelineResult.profile,
        borrower_id: "SHOP-998877",
        account_number: "123456789012",
        upi_id: "shop@upi",
      },
    }, { now, nonceId: "p2".repeat(8) })
    const blob = JSON.stringify(snapshot)
    expect(blob).not.toContain("123456789012")
    expect(blob).not.toContain("shop@upi")
    expect(blob).not.toContain("SHOP-998877")
    expect(snapshot.assessment.borrower_alias).toBeNull()
  })

  it("includes only an explicit user-approved alias, never the raw id used as the alias", () => {
    const approved = createShareableSnapshot(pipelineResult, {
      now,
      nonceId: "p3".repeat(8),
      borrowerAlias: "Kirana Shop",
    })
    expect(approved.assessment.borrower_alias).toBe("Kirana Shop")
    expect(JSON.stringify(approved)).not.toContain("SHOP-998877")

    const spoofed = createShareableSnapshot(pipelineResult, {
      now,
      nonceId: "p4".repeat(8),
      borrowerAlias: "SHOP-998877",
    })
    expect(spoofed.assessment.borrower_alias).toBeNull()
  })
})
