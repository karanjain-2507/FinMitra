# AGENTS.md — Rules & Guidelines for FinMitra Person 1 Subsystem

This document outlines the strict operational constraints and design contracts for any AI coding agent modifying or maintaining Person 1 (`finmitra_person1/`).

---

## Core Operational Rules

1. **Strict Scope Boundary**:
   - You are working **ONLY on Person 1** (Evidence Engine + Ingestion + Normalization).
   - **DO NOT** implement Person 2 (Cash Flow ML prediction), Person 3 (Repayment Engine performance/scoring), or Person 4 (Capacity/Affordability/Readiness Index).
   - **DO NOT** create a creditworthiness scoring model or loan decisioning engine.

2. **Preserve Provenance**:
   - Every normalized transaction **MUST** retain its source origin in the `provenance` field.
   - When deduplicating or matching across sources, merge provenance records; **NEVER delete or overwrite source history**.

3. **Self-Declared Income Policy**:
   - Self-declared cash income must be categorized as `SELF_DECLARED_CASH_INCOME` with `model_eligible = False` and `verification = VerificationLevel.SELF_DECLARED`.
   - Never silently upgrade unverified self-declarations to verified business income unless backed by independent receipts or ledger records.

4. **Numeric and Data Types**:
   - Dates **MUST** use ISO 8601 `YYYY-MM-DD`.
   - Transaction currency amounts **MUST** use integer paise (`amount_paise: int`).
   - Confidence **MUST** be bounded between `0.0` and `1.0` (use `0.85`, never `85`).
   - Evidence score **MUST** be bounded between `0.0` and `100.0`.
   - Missing numeric values **MUST** be `None`, never converted to `0`.
   - Random seeds for anomaly detection **MUST** be `42`.

5. **Explainable Reason Codes**:
   - All diagnostic reasons emitted by Person 1 **MUST** use the `EVxx` prefix (e.g. `EV01` to `EV17`).
   - Reasons must be structured objects containing `code`, `direction`, `impact`, and a human-readable `message`.

6. **Anomaly != Invalidity**:
   - Statistical outliers must be flagged with `anomaly_flag = True` and emit an `EV11` warning.
   - **NEVER** silently discard or delete anomalous transactions from the normalized timeline.

7. **Public Interface Stability**:
   - Maintain the public interfaces in `evidence/engine.py`:
     ```python
     def assess(profile: BorrowerInput) -> EvidenceResult: ...
     def build_evidence_bundle(profile: BorrowerInput) -> EvidenceBundle: ...
     ```
   - Downstream engines (Persons 2, 3, 4) rely on these contract shapes.

8. **Testing Discipline**:
   - Always run `python3 -m pytest -v` and test all CLI fixture runs before finishing any changes.
