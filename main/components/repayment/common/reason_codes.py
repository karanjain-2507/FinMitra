"""Repayment reason codes (RP*). Do not use EV or CF codes in this component."""

RP00_BASELINE = "RP00"
RP01_MATERIALLY_UNPAID = "RP01"
RP02_DELINQUENT = "RP02"
RP03_BEHIND_SCHEDULE = "RP03"
RP04_COMPLETED_CYCLES = "RP04"
RP05_ON_TIME = "RP05"
RP06_OUTSTANDING_PRINCIPAL = "RP06"
RP07_DIGITALLY_MATCHED = "RP07"
RP08_CONTRADICTION = "RP08"
RP09_SUPPLIER_CONFIRMED = "RP09"
RP10_FULLY_REPAID = "RP10"
RP11_INSUFFICIENT_EVIDENCE = "RP11"
RP12_HARD_CAP = "RP12"
RP13_CURRENT_ON_SCHEDULE = "RP13"
RP14_OLD_ACTIVE_MISSING = "RP14"
RP15_DECLARED_COMPLETED_UNDERPAID = "RP15"

REASON_CODES: dict[str, str] = {
    RP00_BASELINE: "Neutral repayment baseline",
    RP01_MATERIALLY_UNPAID: "Materially unpaid overdue obligation",
    RP02_DELINQUENT: "Delinquent loan obligation",
    RP03_BEHIND_SCHEDULE: "Repayment is behind the reconstructed schedule",
    RP04_COMPLETED_CYCLES: "Completed credit cycles",
    RP05_ON_TIME: "On-time installment performance",
    RP06_OUTSTANDING_PRINCIPAL: "Outstanding principal remaining",
    RP07_DIGITALLY_MATCHED: "Digitally matched repayments",
    RP08_CONTRADICTION: "Contradictory repayment declarations",
    RP09_SUPPLIER_CONFIRMED: "Supplier-confirmed repayments",
    RP10_FULLY_REPAID: "Loan fully repaid",
    RP11_INSUFFICIENT_EVIDENCE: "Insufficient repayment evidence",
    RP12_HARD_CAP: "Hard cap applied for serious delinquency",
    RP13_CURRENT_ON_SCHEDULE: "Expected installments paid on schedule",
    RP14_OLD_ACTIVE_MISSING: "Old active loan is missing expected payments",
    RP15_DECLARED_COMPLETED_UNDERPAID: "Declared completed but repayment completion below 90%",
}
