# FinMitra Product Requirements Document

**Document status:** Implementation-ready draft

**Product:** FinMitra

**Workstreams:** What If planning, encrypted QR sharing, localization/simplified language/text-to-speech

**Primary implementation area:** `main/`
**Audience:** Product, engineering, design, QA, and the three workstream owners

---

## 1. Product summary

FinMitra currently evaluates a borrower's transaction evidence, cash-flow stability, repayment behavior, and affordable borrowing capacity. The next product phase must turn those assessments into understandable, actionable financial guidance.

The central product question is:

> Given my current financial situation, what can I realistically do, and what would need to change for me to achieve a specific financial goal?

This phase adds three coordinated capabilities:

1. **What If planning:** backward planning from a financial goal to the changes required to make it feasible.
2. **Encrypted QR sharing:** a secure, consent-based way to transfer a deliberately limited financial summary without putting plaintext financial data in a QR code.
3. **English, Hindi, Punjabi, simplified language, and text-to-speech:** a shared presentation layer that makes FinMitra's calculations understandable without changing their financial meaning.

These capabilities must extend the current application. They must not replace the existing four-engine assessment pipeline or duplicate its calculations in the frontend.

---

## 2. Existing product and architecture

### 2.1 Current user experience

The current React application provides:

- A home page explaining the four-engine assessment.
- Three bundled demonstration scenarios.
- CSV statement upload with borrower, date, source type, household expense, and balance-buffer inputs.
- A result screen containing evidence, cash-flow, repayment, capacity, findings, lineage, and raw JSON.

Assessment results are currently passed between frontend routes through React Router state. There is no persistent user account, server-side session, or database.

### 2.2 Current backend

The FastAPI layer exposes:

- `GET /api/health`
- `GET /api/demo/{scenario}`
- `POST /api/assess`
- `POST /api/assess/csv`

The integrated pipeline accepts an `IntegratedBorrowerInput`, runs four isolated engines, and returns an assessment containing:

- Evidence quality, confidence, provenance, and warnings.
- Cash-flow stress probability and derived cash-flow features.
- Repayment status and `new_credit_blocked` policy decision.
- Monthly surplus, safe EMI range, maximum principal by tenure, loan assessment, and stress tests.

### 2.3 Reusable financial fields

The following existing fields are authoritative inputs for this phase:

| Need | Existing source |
|---|---|
| Conservative monthly income | `profile.capacity.features.conservative_monthly_inflow` |
| Household essentials | `profile.capacity.features.essential_household_expense` |
| Business essentials | `profile.capacity.features.essential_business_expense` |
| Formal EMI obligations | `profile.capacity.features.existing_formal_emis` |
| Informal installments | `profile.capacity.features.existing_informal_installments` |
| Monthly surplus | `profile.capacity.features.monthly_surplus` |
| Available buffer | `profile.capacity.features.available_balance_buffer` |
| Income volatility | `profile.capacity.features.income_volatility` |
| Safe EMI range | `profile.safe_emi` and `profile.capacity.safe_emi` |
| Affordable principal | `profile.capacity.max_principal` |
| Specific loan feasibility | `profile.capacity.requested_loan` |
| Delinquency block | `profile.repayment.new_credit_blocked` |
| Data confidence | Component confidence fields and `profile.overall_confidence` |
| Adverse-condition resilience | `profile.capacity.stress_tests` |

### 2.4 Current limitations relevant to this phase

- There is no general-purpose savings balance. `available_balance_buffer` must not automatically be presented as spendable savings.
- There is no transaction-editing or budget-management workflow.
- There is no persistent assessment identifier or profile store.
- Human-readable engine reasons are currently English strings, although reason codes and structured numeric fields exist.
- There is no authentication, encryption service, key store, or revocation store.
- The cash-flow model is demo-grade and trained on synthetic outcomes. Recommendations must be framed as planning guidance, not guaranteed eligibility or regulated financial advice.
- API runtime packages used by the existing server are not all declared in `main/requirements.txt`; dependency hygiene is a shared prerequisite.

---

## 3. Product principles

All three owners must follow these principles:

1. **One calculation, many presentations.** Financial math produces structured, language-neutral results. Translation and speech consume those results.
2. **Explain the gap.** A feasibility label alone is insufficient. The user must see current capacity, required capacity, the gap, assumptions, and potential ways to close it.
3. **No invented certainty.** FinMitra must clearly distinguish derived values, user-declared values, policy assumptions, and unavailable data.
4. **Preserve hard safety decisions.** A repayment hard block cannot be bypassed by a What If scenario.
5. **Minimize sensitive data.** QR payloads contain only fields required for the chosen sharing purpose.
6. **Encryption is not encoding.** Base64, compression, and QR encoding provide no confidentiality.
7. **User control.** Sharing, scanning, language changes, simplified explanations, and speech are explicit user actions.
8. **Accessible by default.** Touch targets, focus states, screen-reader labels, contrast, responsive layout, and reduced-motion preferences are requirements.
9. **No hidden mutation.** A scenario does not alter the source assessment or claim that the user's real finances have changed.

---

## 4. Goals and success measures

### 4.1 Product goals

- Allow a user to test a concrete financial goal against their actual FinMitra assessment.
- Produce deterministic, auditable, structured recommendations.
- Allow a user to understand the same result in English, Hindi, or Punjabi.
- Offer a simpler explanation without changing any number or conclusion.
- Allow important results to be read aloud on demand.
- Allow a user to share a deliberately limited financial summary through an encrypted QR workflow.
- Preserve compatibility with all existing demos, CSV assessment, tests, and component contracts.

### 4.2 Initial success measures

Instrumentation should be privacy-preserving and exclude raw financial values.

| Measure | Initial target |
|---|---:|
| Users who complete a started What If flow | 70% or more |
| Completed plans that show all required explanation sections | 100% |
| Numeric parity across all three languages | 100% |
| QR tamper/wrong-key rejection in automated tests | 100% |
| QR creation events that contain plaintext sensitive fields | 0 |
| Existing integrated pipeline regressions | 0 |
| Critical flows usable at 360 px viewport width | 100% |

### 4.3 Non-goals for this phase

- Loan approval, lender matching, or a promise of approval.
- Automated movement of money or automatic budget changes.
- Investment, tax, or legal advice.
- Predicting future income with certainty.
- Continuous microphone listening or automatic speech playback.
- Sharing full transaction histories through QR.
- Building user accounts, cloud synchronization, or a long-term financial-record database unless separately approved.
- Adding languages beyond English, Hindi, and Punjabi.

---

## 5. Shared product flow

1. The user runs or opens a valid FinMitra assessment.
2. The result screen offers **Plan a goal** and **Share securely** actions.
3. What If uses the assessment as an immutable baseline and collects only missing goal inputs.
4. The backend returns a structured plan with current state, required state, gap, scenarios, assumptions, and warnings.
5. The presentation layer renders that result in the selected language and optional simplified mode.
6. The user may start or stop speech for a defined result summary.
7. If the user chooses to share, the QR flow creates a purpose-limited snapshot, encrypts it, and generates a QR representation.
8. A recipient scans/imports, decrypts, validates, previews, and explicitly accepts the snapshot.

---

# Workstream 1 — Person 1: What If financial planning

## 6. Workstream objective

Build a backward-planning feature that compares a user's assessed financial position with a desired goal and shows what must change, by how much, and within what timeframe.

This is not a standalone EMI calculator. Existing FinMitra assessment fields and policies remain the source of truth.

## 7. Supported goal types

### 7.1 Required MVP goal: prepare for a loan

Required user inputs:

- Goal title or purpose, such as car, equipment, education, or working capital.
- Requested principal in INR.
- Expected annual interest rate.
- Loan tenure in months.
- Readiness deadline in months.

The deadline means “when I want my finances to be ready to support this commitment,” not the loan repayment tenure.

### 7.2 Recommended second MVP goal: reach a savings target

Required user inputs:

- Goal title or purpose.
- Target amount in INR.
- Current amount already set aside specifically for this goal.
- Deadline in months.

The current goal savings must be explicitly declared. The system must not silently use `available_balance_buffer` as goal savings.

### 7.3 Post-MVP goals

- Prepare for a one-time purchase.
- Test a new recurring monthly commitment.
- Compare two deadlines or two loan configurations.

Post-MVP types should reuse the same structured result contract rather than create separate result-page architectures.

## 8. What If user experience

### 8.1 Entry points

- Primary action on a completed assessment result: **Plan a goal**.
- Navigation item: **What If**. If no assessment is available, direct the user to run an assessment first.
- Demo scenarios may offer prefilled example goals, but every result must still use the selected demo's real assessment values.

### 8.2 Goal form

The form must:

- Show only fields relevant to the selected goal type.
- Format INR values using Indian digit grouping.
- Explain interest rate, tenure, and deadline in simple language.
- Validate positive amounts, reasonable month bounds, and complete loan-field groups.
- Preserve entered values when navigating between form and result during the same browser session.
- Avoid free-form natural-language parsing in MVP; a purpose label plus structured numeric fields is safer and testable.

### 8.3 Result sections

Every result must contain:

1. **Your goal:** purpose, amount, deadline, and applicable loan terms.
2. **Where you are now:** authoritative current income/capacity/obligation values used in the calculation.
3. **What the goal requires:** required monthly contribution or EMI and required surplus/capacity.
4. **The gap:** rupee amount per month and total amount where relevant.
5. **Possible paths:** deterministic scenarios such as expense reduction, additional monthly income, deadline extension, lower principal, or mixed changes.
6. **Safety checks:** delinquency block, data sufficiency, stress-test failures, and buffer warnings.
7. **Assumptions:** rate, tenure, policy factors, user-declared values, and rounding.
8. **Plain-language conclusion:** achievable now, achievable with changes, blocked, or insufficient data.

## 9. Calculation requirements

### 9.1 Baseline

Use the completed integrated assessment. Do not recalculate cash-flow or capacity rules in React.

At minimum, capture:

```text
current_monthly_surplus
current_safe_emi_min
current_safe_emi_max
current_available_buffer
current_obligations
new_credit_blocked
overall_confidence
stress_test_results
```

### 9.2 Loan goal

Use the existing amortizing-loan EMI formula already used by the capacity engine. The same principal, interest rate, and tenure must return the same EMI in both capacity and What If.

Derive:

```text
required_emi
emi_gap = max(0, required_emi - current_safe_emi_max)
required_surplus = required_emi / active_safe_emi_max_factor
monthly_cashflow_gap = max(0, required_surplus - current_monthly_surplus)
```

The active policy factor must come from the capacity result or shared policy configuration; do not hard-code `0.50` in the frontend.

If the user is already within safe capacity, the plan should say so while still showing stress-test and buffer limitations.

If `new_credit_blocked` is true:

- Outcome is `BLOCKED` regardless of apparent surplus.
- Do not offer expense reduction or income increase as a way to override the block.
- Explain that the unresolved repayment issue must be addressed first.
- Preserve the original repayment reason codes and outstanding values where available.

### 9.3 Deadline meaning for a loan goal

The deadline drives the action plan, not the EMI amortization.

- Show the monthly cash-flow improvement that must be established by the deadline.
- If the user supplies a desired readiness buffer, compute the additional monthly buffer contribution over the deadline.
- Without an explicit desired buffer, do not invent a mandatory savings target. Surface relevant existing stress-test buffer shortfalls separately.
- Allow an “extend readiness deadline” scenario only for accumulated buffer/savings gaps. Extending the readiness deadline does not reduce the eventual EMI.

### 9.4 Savings goal

Derive:

```text
remaining_target = max(0, target_amount - current_goal_savings)
required_monthly_saving = remaining_target / deadline_months
monthly_gap = max(0, required_monthly_saving - current_monthly_surplus)
projected_amount = current_goal_savings + max(0, current_monthly_surplus) * deadline_months
```

The result must warn that using all monthly surplus may leave no margin for unexpected costs. A conservative recommended contribution may be shown only if its policy factor is explicit and returned as an assumption.

### 9.5 Scenario generation

Possible paths must be calculation-backed, not generic prose. Return structured scenarios such as:

```json
{
  "type": "REDUCE_EXPENSES",
  "monthly_amount": 4200,
  "new_deadline_months": null,
  "new_principal": null,
  "message_key": "whatIf.path.reduceExpenses"
}
```

Required scenario rules:

- Never return negative required changes.
- Never recommend reducing expenses below zero.
- Clearly label income increases and expense reductions as hypothetical.
- A mixed path must show each component separately and total to the same gap within rounding tolerance.
- A deadline-extension scenario must include the recalculated monthly contribution.
- A reduced-principal loan scenario must use the existing affordability calculation, not proportional approximation.
- Rank paths by smallest behavioral change, but do not claim that a path is easy or guaranteed.

### 9.6 Outcome states

Use stable machine-readable states:

- `ACHIEVABLE_NOW`
- `ACHIEVABLE_WITH_CHANGES`
- `BLOCKED`
- `INSUFFICIENT_DATA`
- `INVALID_GOAL`

Presentation text must be selected from these states and numeric fields, not parsed from backend English sentences.

## 10. What If API contract

Recommended endpoint:

```http
POST /api/what-if
Content-Type: application/json
```

Recommended request:

```json
{
  "assessment_id": "opaque-server-issued-id",
  "goal": {
    "type": "LOAN_READINESS",
    "title": "Car",
    "target_amount": 100000,
    "deadline_months": 8,
    "annual_interest_rate": 0.14,
    "tenure_months": 24,
    "current_goal_savings": null,
    "desired_buffer": null
  }
}
```

Assessment endpoints issue a short-lived opaque `assessment_id`. The backend must resolve that ID to an immutable server-owned assessment snapshot and must reject client-supplied assessment inputs or derived baseline fields. Unknown or expired IDs return `404` and require a fresh assessment.

Recommended response:

```json
{
  "schema_version": "1.0",
  "calculation_version": "1.0",
  "outcome": "ACHIEVABLE_WITH_CHANGES",
  "goal": {},
  "current_state": {},
  "required_state": {},
  "gap": {},
  "paths": [],
  "safety": {},
  "assumptions": [],
  "message_keys": []
}
```

CSV assessments may initially pass the original assembled input forward in in-memory route state. A later persistence phase can replace this with an opaque assessment ID.

## 11. What If file ownership

Person 1 should own new files under:

- `main/finmitra/what_if/`
- `main/frontend/src/pages/WhatIf.jsx`
- `main/frontend/src/components/what-if/`
- `main/tests/test_what_if.py`

Person 1 may propose changes to shared files but should coordinate before editing:

- `main/api_server.py`
- `main/frontend/src/App.jsx`
- `main/frontend/src/api.js`
- `main/frontend/src/components/layout/TopBar.jsx`
- `main/frontend/src/pages/Result.jsx`

## 12. What If acceptance criteria

- A strong demo can produce a loan-readiness plan using its actual capacity values.
- An unpaid-loan demo always returns `BLOCKED` and cannot be made “achievable” by changing expenses.
- A thin-history demo returns `INSUFFICIENT_DATA` where authoritative inputs are unavailable.
- EMI equals the capacity engine's EMI for identical loan terms within one paisa.
- Every rupee figure in the conclusion can be traced to a response field.
- Changing the readiness deadline does not incorrectly change the loan EMI.
- Savings plans never treat the liquidity buffer as goal savings without explicit consent.
- The original assessment object remains unchanged after scenario calculation.
- Boundary, rounding, zero-rate, short-deadline, large-amount, and invalid-input tests pass.

---

# Workstream 2 — Person 2: Encrypted QR sharing

## 13. Workstream objective

Allow a user to deliberately share or transfer a limited FinMitra financial snapshot through a QR code while maintaining confidentiality, integrity, validation, and user control.

## 14. Sharing purpose and data minimization

The MVP sharing purpose is:

> Transfer a concise FinMitra assessment or What If summary to another FinMitra session with the user's explicit consent.

The MVP QR must not include:

- Raw bank transactions.
- Uploaded files.
- Account numbers, UPI IDs, merchant identifiers, or counterparty names.
- Full evidence provenance.
- Free-form metadata.
- Encryption keys or passphrases.

The user must see a pre-encryption preview listing exactly what will be shared.

### 14.1 Recommended transferable snapshot

```json
{
  "schema_version": "1.0",
  "purpose": "FINMITRA_SUMMARY_TRANSFER",
  "issued_at": "ISO-8601 timestamp",
  "expires_at": "ISO-8601 timestamp",
  "nonce_id": "random identifier",
  "assessment": {
    "borrower_alias": "optional user-approved alias",
    "evaluation_date": "YYYY-MM-DD",
    "readiness_index": 56.55,
    "overall_confidence": 0.62,
    "cashflow_status": "SUFFICIENT",
    "repayment_status": "CURRENT",
    "new_credit_blocked": false,
    "monthly_surplus": 13625,
    "safe_emi_min": 5450,
    "safe_emi_max": 6812.5
  },
  "what_if": null
}
```

Optional What If content should include goal type, target, deadline, outcome, and gap—not the entire source assessment.

## 15. Security architecture

### 15.1 MVP mode: passphrase-protected portable QR

Because the current application has no accounts, database, or key service, use client-side envelope encryption:

1. Build and validate the minimized snapshot.
2. Serialize deterministically.
3. Optionally compress before encryption if browser support and tests are reliable.
4. Derive a key from a user-entered sharing passphrase using a modern KDF with a random salt and documented work factor.
5. Encrypt with an authenticated encryption mode such as AES-256-GCM using a fresh random IV/nonce for every QR.
6. Place only version, KDF parameters, salt, IV, and ciphertext in the QR envelope.
7. Communicate the passphrase separately from the QR.

Web Crypto must be used rather than handwritten cryptography.

### 15.2 Required envelope properties

- `version`
- `algorithm`
- `kdf`
- `kdf_iterations` or equivalent cost parameters
- Random `salt`
- Random encryption `iv`
- Authenticated `ciphertext`
- Optional non-sensitive content-type marker

Binary values may be base64url-encoded after encryption. The documentation and UI must not call base64 encryption.

### 15.3 Future online mode

If a backend store and authentication are later approved, the preferred high-volume design is an opaque, random, short-lived token in the QR with encrypted server-side content, expiry, one-time access, and revocation. This is out of scope for the offline MVP and must not be simulated with an in-memory production store.

## 16. QR creation flow

1. User selects **Share securely**.
2. User chooses assessment summary, What If summary, or both.
3. FinMitra displays included and excluded fields.
4. User chooses an expiry period from approved options.
5. User enters and confirms a passphrase; strength guidance is shown.
6. FinMitra encrypts locally and generates the QR.
7. UI reminds the user to send the passphrase through a separate channel.
8. User may hide/reveal the QR and explicitly destroy the local sharing session.

Do not render a QR until encryption succeeds.

## 17. QR scan/import flow

1. User selects **Scan secure QR** or imports a QR image.
2. Camera permission is requested only after the user starts scanning.
3. Scanner reads the encrypted envelope.
4. FinMitra validates envelope size, version, algorithm identifiers, and required fields before asking for decryption.
5. User enters the separately received passphrase.
6. Authenticated decryption either succeeds or returns a generic failure.
7. Decrypted content is schema-validated and checked for expiry and purpose.
8. User sees a preview and explicitly chooses **Use this summary** or **Discard**.
9. Decrypted content is not logged and is removed from local state on discard/navigation where practical.

## 18. Error handling

Required user-visible states:

- QR not recognized as FinMitra data.
- Unsupported envelope version.
- Payload too large.
- Wrong passphrase or modified payload. These should share a generic failure message to avoid leaking verification detail.
- Expired snapshot.
- Valid encryption but invalid inner schema.
- Camera unavailable or permission denied.
- No supported scanner API; offer image upload/manual encrypted-text import where feasible.

No error response or console log may contain decrypted financial content, the passphrase, derived key, or raw ciphertext beyond what is necessary for debugging in non-production tests.

## 19. QR capacity and usability

- Keep the encrypted envelope well below practical QR scanning limits.
- Reject oversized snapshots before encryption and explain which optional content can be removed.
- Use an error-correction level appropriate for on-screen scanning and test on low-end phone cameras.
- Display adequate quiet zone, contrast, and minimum size.
- Provide a non-visual encrypted-text export/import fallback for accessibility.
- Do not use animated or multi-frame QR for MVP.

## 20. QR dependencies and implementation boundary

Person 2 owns:

- `main/frontend/src/security/`
- `main/frontend/src/components/qr/`
- `main/frontend/src/pages/SecureShare.jsx`
- `main/frontend/src/pages/SecureImport.jsx`
- Frontend cryptography, serialization, QR generation, and scan/import tests.

Any QR/scanner dependency must be actively maintained, browser-compatible, license-compatible, and locked in `package-lock.json`.

Person 2 must coordinate changes to shared routes, navigation, and result actions. Person 2 must not add server secrets or commit `.env` contents.

## 21. QR acceptance criteria

- Searching the decoded QR data does not reveal borrower alias, amounts, statuses, or other snapshot values.
- Identical snapshots encrypted twice produce different envelopes because salt/IV values are fresh.
- Changing any ciphertext byte causes authenticated decryption failure.
- A wrong passphrase never produces a partially rendered result.
- Expired and unsupported-version snapshots cannot be imported.
- Inner payloads with extra forbidden fields are rejected.
- No raw transactions are selectable for sharing.
- Passphrase and key material never appear in analytics, logs, URLs, localStorage, or the QR.
- Camera scanning and image import are both covered by tests or documented capability fallbacks.
- QR pages remain usable with keyboard and screen reader.

---

# Workstream 3 — Person 3: Localization, simplified language, and TTS

## 22. Workstream objective

Make FinMitra's assessment and What If guidance understandable in exactly three languages—English, Hindi, and Punjabi—while preserving numeric meaning and giving users explicit control over simpler explanations and speech.

## 23. Locale requirements

Supported locale identifiers:

- English: `en-IN`
- Hindi: `hi-IN`
- Punjabi: `pa-IN`

Punjabi MVP uses Gurmukhi script. Do not add a Shahmukhi or transliterated-Punjabi mode under the same locale without a separate product decision.

### 23.1 Language selection

- Persistent language selector in the global header.
- Language names shown in their own language: English, हिन्दी, ਪੰਜਾਬੀ.
- Selection saved locally on the device without storing financial data.
- Default to `en-IN` when no supported preference exists.
- Changing language must not rerun calculations or reset form/result state.
- HTML `lang` should reflect the active locale.

## 24. Translation architecture

All new UI strings must use stable translation keys. What If conclusions must be assembled from structured values and message keys.

Example:

```json
{
  "key": "whatIf.gap.monthly",
  "params": {
    "amount": 4200,
    "months": 8
  }
}
```

Required translation namespaces:

- `common`
- `navigation`
- `assessment`
- `whatIf`
- `secureShare`
- `errors`
- `speech`

Do not use translated display text as program logic, enum values, analytics identifiers, or API values.

### 24.1 Existing backend English reasons

Existing reason objects contain stable codes plus English messages. The localization layer should:

1. Map known reason codes and structured numeric fields to localized templates.
2. Fall back to the backend message in English when a code is unknown.
3. Clearly mark or log a missing translation key in development without exposing financial data.
4. Never attempt to extract financial values by parsing the English message.

If required numeric parameters are not currently structured, coordinate a contract extension rather than duplicating regex parsing in the frontend.

## 25. Simplified financial language

Simplified mode is independent of language. A user may choose standard or simple explanations in English, Hindi, or Punjabi.

Each important concept should have:

- A short familiar label.
- A one-sentence plain-language explanation.
- The authoritative number.
- An optional “technical details” disclosure.

Example structure:

```text
Safe monthly EMI
An instalment range your current monthly surplus may support.
₹5,450–₹6,812 per month
[How this was calculated]
```

### 25.1 Terminology rules

- Do not translate financial terms word-for-word when a familiar local-language explanation is clearer.
- Keep common terms such as EMI where users recognize them, followed by an explanation on first use.
- Preserve qualifiers such as “estimated,” “current,” “monthly,” “up to,” and “under these assumptions.”
- Never simplify away a warning, hard block, uncertainty, interest rate, timeframe, or negative value.
- Do not change the outcome severity between standard and simple modes.
- Avoid shame-oriented language about debt, low income, missing records, or delinquency.

### 25.2 Required glossary concepts

The reviewed glossary must cover at least:

- Monthly income/inflow
- Essential expenses
- Monthly surplus
- Existing obligation
- EMI
- Safe EMI
- Interest rate
- Loan tenure
- Readiness deadline
- Financial gap
- Cash-flow stress
- Income volatility
- Buffer/emergency reserve
- Delinquency/overdue payment
- Confidence/data completeness
- What If scenario
- Encryption
- Secure sharing passphrase
- Expiry

Translations require review by financially literate native speakers of Hindi and Punjabi before release.

## 26. Number, currency, and date formatting

- Keep all API numbers numeric; localize only at presentation time.
- Use `Intl.NumberFormat` with the selected locale and INR currency.
- Use Indian grouping where supported and test lakh/crore values explicitly.
- Do not translate or alter raw numeric values.
- Percentages must distinguish ratios from percentages; `0.14` annual interest is displayed as `14%`, not `0.14%`.
- Dates should use locale-aware formatting while retaining unambiguous machine values in APIs.
- For speech, expand symbols such as ₹ and `%` into locale-appropriate spoken phrases.

## 27. Text-to-speech experience

Use the browser Speech Synthesis API for MVP, with graceful degradation.

### 27.1 Speech controls

- Explicit **Listen** button near important assessment and What If summaries.
- **Pause/Resume** where supported.
- **Stop** always available while speaking.
- Starting a new narration stops the previous narration.
- Navigating away or changing language stops current speech.
- No automatic playback on page load, result completion, language change, or QR import.

### 27.2 Narration content

Narration should include, in this order:

1. Goal and deadline.
2. Current monthly position.
3. Required monthly amount or EMI.
4. The monthly gap.
5. Top one or two possible changes.
6. Blocking condition or important warning.
7. Statement that the result is based on current data and assumptions.

Do not narrate raw JSON, internal codes, every chart point, or the entire audit trail by default.

### 27.3 Voice selection

- Request voices matching `en-IN`, `hi-IN`, or `pa-IN`.
- If an exact voice is unavailable, use the closest matching language voice and disclose that pronunciation may vary.
- If no usable voice exists, disable Listen with a clear explanation; do not silently speak Punjabi or Hindi using an English voice.
- Voice availability differs by browser and operating system and must not block the visual experience.

### 27.4 Speech safety and privacy

- Speech is opt-in and may be audible to nearby people; show a brief first-use privacy hint.
- Narration text stays in memory only as needed for playback.
- Do not send financial narration to a third-party cloud TTS service in MVP.
- Do not include the sharing passphrase, encryption material, raw account data, or hidden fields in speech.

## 28. Localization file ownership

Person 3 owns:

- `main/frontend/src/i18n/`
- `main/frontend/src/locales/en-IN/`
- `main/frontend/src/locales/hi-IN/`
- `main/frontend/src/locales/pa-IN/`
- `main/frontend/src/components/accessibility/SpeechControls.jsx`
- `main/frontend/src/hooks/useSpeechSynthesis.js`
- Translation completeness, numeric parity, simplified-language, and speech tests.

Person 3 coordinates changes to every existing page because current UI copy is hard-coded English. Shared routing or layout changes must be merged through the agreed integrator.

## 29. Localization and TTS acceptance criteria

- Every user-facing string in the three new workstreams is available in all three languages.
- A missing translation falls back safely to English without a blank or crash.
- Switching language preserves the active assessment, form values, and What If result.
- All three languages display identical numeric values after locale formatting.
- Simplified mode changes wording but not values, warning severity, or outcomes.
- Known backend reason codes render through localized structured templates.
- Listen, pause/resume, and stop controls have accessible names and visible state.
- Speech stops on navigation, language change, explicit stop, and component unmount.
- Unsupported Punjabi/Hindi voices produce a clear fallback state.
- No page speaks automatically.

---

## 30. Shared contracts between owners

### 30.1 Structured result contract

Person 1 must provide Person 3 with:

- Stable outcome enums.
- Stable scenario-type enums.
- Numeric parameters separate from prose.
- Message keys for conclusions, assumptions, warnings, and paths.
- A schema version and calculation version.

Person 3 must not fork or reproduce Person 1's calculations.

### 30.2 Shareable result contract

Person 1 defines which structured What If fields are safe and meaningful to share. Person 2 maintains an explicit allowlist and rejects all unspecified fields.

Person 2 must not serialize full route state or raw API responses into a QR.

### 30.3 Localized QR experience

Person 2 supplies stable error/status identifiers. Person 3 supplies localized display copy. Cryptographic algorithm names and envelope enum values remain unchanged across languages.

### 30.4 Versioning

The following versions must be independent:

- Integrated assessment pipeline version.
- What If schema/calculation version.
- QR envelope version.
- Shareable snapshot schema version.
- Translation catalog version, if tracked.

Readers must reject unsupported security/schema versions rather than guessing.

---

## 31. Shared API and state requirements

### 31.1 Short-term state

For MVP, assessment input/result and What If result may remain in memory or route state. Refresh limitations must be made clear, and QR sharing must never rely on hidden global mutable state.

### 31.2 Recommended future state

A later phase may add an authenticated, encrypted assessment store and opaque assessment IDs. The three workstreams should keep API contracts serializable so this can be introduced without rewriting calculations or presentation.

### 31.3 Validation

- Backend validates every financial input used for calculations.
- Frontend validation improves usability but is not authoritative.
- Imported decrypted content is untrusted until schema validation succeeds.
- Unknown fields are rejected for financial and shared-payload schemas unless explicitly designed for forward compatibility.

---

## 32. Privacy, safety, and compliance requirements

- Collect only values required for the chosen goal or share purpose.
- Do not log uploaded statement rows, decrypted QR content, passphrases, keys, or complete financial results.
- Avoid including financial values in URLs, analytics labels, exception text, or browser history.
- Results must state that they are estimates based on provided/current data and assumptions.
- Do not use “approved,” “guaranteed,” or equivalent wording.
- Hard blocks and insufficient-data states must remain visible in every language and simplified mode.
- Provide a way to discard imported/shared data from the current session.
- Add a security review checkpoint before QR release.
- Add native-speaker and financial-content review before localization release.

---

## 33. Accessibility and responsive requirements

- Meet WCAG 2.1 AA color contrast for text and controls.
- All workflows operable with keyboard alone.
- Visible focus indicator on language, speech, QR, form, and scenario controls.
- Form errors associated with their fields and announced to assistive technology.
- Charts must have equivalent text summaries.
- Do not rely on green/red alone for achievable, warning, or blocked states.
- QR has a textual description and encrypted-text alternative.
- Test at 360 px, 768 px, and desktop widths.
- Respect reduced-motion preferences.

---

## 34. Test strategy

### 34.1 Existing regression gate

- Existing integrated pipeline tests must pass.
- Existing frontend build must pass.
- Existing demo, JSON, and CSV assessment flows must remain functional.

### 34.2 Person 1 tests

- Unit tests for every goal calculation and outcome transition.
- Parity tests against capacity-engine EMI.
- Policy-factor and rounding tests.
- Hard-block and insufficient-data tests.
- Property/boundary tests for non-negative gaps and internally consistent paths.
- API validation and serialization tests.

### 34.3 Person 2 tests

- Encryption/decryption round trip.
- Fresh salt and IV.
- Wrong-passphrase and tamper rejection.
- Expiry, version, purpose, schema, oversized-payload, and forbidden-field rejection.
- No secret persistence/logging tests where practical.
- QR encode/decode interoperability with representative mobile scan fixtures.

### 34.4 Person 3 tests

- Translation-key completeness across all locales.
- Numeric parity snapshots for English, Hindi, and Punjabi.
- Simple/standard mode parity.
- Locale currency, percent, and date tests.
- Speech lifecycle tests using a mocked Speech Synthesis API.
- Accessibility tests for selector and speech controls.

### 34.5 End-to-end scenarios

At minimum:

1. Strong borrower plans an affordable loan, switches to Hindi, and listens to the result.
2. Strong borrower selects a larger loan and sees a quantified monthly gap and alternatives.
3. Unpaid borrower is blocked in all languages, including simplified mode.
4. Thin-history borrower receives an insufficient-data explanation.
5. User creates an encrypted summary QR, recipient decrypts it, and reviews the same numeric result in Punjabi.
6. Modified, expired, oversized, and wrong-passphrase QR payloads fail safely.

---

## 35. Delivery sequence and merge coordination

### Phase 0 — Shared foundation

1. Declare missing backend runtime dependencies.
2. Agree on shared file integrator and branching convention.
3. Freeze What If result schema, message-key rules, and QR share allowlist.
4. Add shared test fixtures for strong, blocked, and insufficient-data cases.

### Phase 1 — Parallel implementation

- Person 1 builds the calculation engine and API first, then UI.
- Person 2 builds envelope crypto and validation with synthetic allowlisted fixtures, then QR UI.
- Person 3 builds locale infrastructure, formatters, glossary, and speech controls, then integrates What If keys as Person 1 stabilizes them.

### Phase 2 — Integration

1. Add navigation and result-page entry actions through the designated integrator.
2. Connect structured What If fields to all language catalogs.
3. Connect the approved summary allowlist to encrypted sharing.
4. Run cross-workstream E2E and accessibility tests.
5. Complete security and translation reviews.

### Phase 3 — Release readiness

- Confirm no plaintext financial data is present in QR fixtures or analytics.
- Confirm numeric parity across locales.
- Confirm existing pipeline regressions remain green.
- Document browser support and speech/scanner fallbacks.
- Add user-facing limitations and privacy guidance.

---

## 36. Shared-file conflict plan

The following files are expected merge hotspots and should have a single integrator or serialized edits:

- `main/api_server.py`
- `main/requirements.txt`
- `main/frontend/package.json`
- `main/frontend/package-lock.json`
- `main/frontend/src/App.jsx`
- `main/frontend/src/api.js`
- `main/frontend/src/components/layout/TopBar.jsx`
- `main/frontend/src/pages/Result.jsx`
- `main/frontend/src/index.css`

Owners should keep most work inside their dedicated directories and submit small, clearly separated changes to the shared files.

---

## 37. Definition of done

The phase is complete only when:

- A user can run an assessment and create a calculation-backed What If plan.
- The plan explains current state, required state, gap, possible paths, warnings, and assumptions.
- Blocked and insufficient-data profiles behave safely.
- Every new flow works in English, Hindi, and Punjabi with numeric parity.
- Simplified mode and opt-in speech work without changing financial meaning.
- An allowlisted summary can be encrypted, represented as QR, scanned/imported, authenticated, validated, previewed, and discarded.
- Wrong keys, tampering, expiry, unsupported versions, and invalid schemas fail safely.
- No hard-coded encryption secrets or plaintext sensitive QR data exist.
- Existing FinMitra assessment functionality remains intact.
- Automated tests, frontend build, security review, accessibility review, and native-language review pass.

---

## 38. Open product decisions

These decisions should be recorded before final UI integration, but they do not block isolated engine/foundation work:

1. Who is the designated integrator for shared React and FastAPI files?
2. Is savings-target support required in the first release, or immediately after loan readiness?
3. What maximum and minimum deadlines should the goal form allow?
4. Which expiry choices should secure sharing offer?
5. Is a borrower alias allowed in a shared snapshot, and should it default to excluded?
6. Is encrypted QR intended only for device-to-device transfer, or for presentation to a lender/partner? The latter requires consent language, recipient expectations, and likely an authenticated online design.
7. Who will perform Hindi and Punjabi financial-language review?
8. Which browsers and mobile devices define the supported scanner and speech matrix?
