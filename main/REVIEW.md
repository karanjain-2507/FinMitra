# Four-person integration review

## What was good

- Person 1 has a complete evidence pipeline with provenance, deduplication,
  anomaly flags, confidence, and 60 passing tests.
- Person 2 has a versioned trained artifact, temporal feature pipeline,
  out-of-distribution checks, explanations, and 39 passing tests.
- Person 3 has deterministic repayment scheduling and a non-negotiable hard
  block for materially unpaid obligations, with 44 passing tests.
- Person 4 has clear affordability policies, stress tests, conservative
  confidence fusion, and 158 passing tests.

## Integration problems found and fixed

1. Person 4's runnable pipeline used mock outputs for Persons 1–3. The new
   runner calls every real engine.
2. Person 1 emits `counterparty_id`/`counterparty_name` and provenance as a
   list; Person 2 expects `counterparty` and provenance as a mapping. An
   explicit adapter now translates without discarding lineage.
3. Person 2's monetary features are in paise while Person 4 expects INR. The
   capacity adapter now performs an explicit `/ 100` conversion.
4. Person 1 used the machine's current date while Persons 2 and 3 used an
   evaluation date. All engines now share the same deterministic cutoff.
5. Person 2 legitimately returns `score=None` for thin history, but Person 4
   rejected it. Thin history now yields `readiness_index=None`; it never gets
   converted into a fake neutral or strong score.
6. Person 4 dropped upstream `status` and Person 3's `hard_cap`. Both are now
   retained in the final profile.
7. Repayment claims can reference a source record that Person 1 deduplicated.
   The adapter resolves source and linked IDs to the canonical transaction.
8. The four packages use conflicting top-level module names such as `common`
   and `schemas`. Components run behind isolated JSON process boundaries, so
   imports cannot silently resolve to another person's package.

## Important limitations still open

- Person 2's model is trained on synthetic outcomes. It is demo-grade, not a
  bank-valid probability model. Real repayment outcomes, time-based validation,
  calibration, subgroup/fairness checks, and drift monitoring are required.
- Raw source ingestion is file-based. Production needs consented Account
  Aggregator/bank/UPI/ledger connectors, encryption, revocation, retention, and
  audit controls.
- Undeclared informal loans cannot be detected reliably. Lender/supplier
  confirmation or a trusted obligation registry is needed to reduce omission
  fraud.
- Household essentials and current balance buffer remain declared inputs.
  Their provenance and verification should be surfaced in a bank-facing report.
- Transaction categorization is heuristic. Low-confidence categories should be
  reviewed instead of presented as facts.
- The readiness index is decision support, not a replacement for a regulated
  bureau score or a bank's underwriting policy.
