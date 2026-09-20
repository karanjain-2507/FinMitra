# Person 1 Implementation Plan — What If Financial Planning

**Owner:** Person 1

**Scope:** Goal input, deadline, backward financial planning, calculation engine, API, and What If UI

**Primary source:** `FINMITRA_PRODUCT_REQUIREMENTS.md`

**Primary implementation area:** `main/`
**Status:** Ready for implementation after contract review

---

## 1. Mission

Build FinMitra's What If feature so a user can start from a financial goal and understand:

- Their current assessed financial position.
- What the goal financially requires.
- Whether it is feasible now.
- The monthly or total gap.
- Which measurable changes could close the gap.
- Which safety conditions or data limitations affect the answer.

The feature must reuse the existing FinMitra assessment and capacity calculations. It must not become an isolated EMI calculator or duplicate financial logic in React.

---

## 2. Person 1 boundaries

### Person 1 owns

- What If domain schemas.
- What If deterministic calculation engine.
- Goal validation.
- Loan-readiness and savings-target calculations.
- Structured result and scenario contracts.
- What If API endpoints.
- Goal form and results UI.
- Unit, API, integration, and frontend tests for What If.
- Documentation of formulas and assumptions.
- Handoff contracts for localization and encrypted sharing.

### Person 1 does not own

- Translation catalogs or language selection.
- Simplified-language copy review.
- Speech synthesis.
- QR encryption, generation, or scanning.
- Changes to the four existing evidence/cash-flow/repayment/capacity engines unless a demonstrated defect blocks What If.
- A database, authentication system, or permanent financial profile store.

### Shared files requiring coordination

Do not independently make broad edits to these files without informing the shared integrator:

- `main/api_server.py`
- `main/requirements.txt`
- `main/frontend/src/App.jsx`
- `main/frontend/src/api.js`
- `main/frontend/src/components/layout/TopBar.jsx`
- `main/frontend/src/pages/Result.jsx`
- `main/frontend/src/index.css`

Keep shared-file changes small and in separate commits.

---

## 3. Existing integration points

### Backend

- Canonical input: `main/finmitra/schemas.py`
- Pipeline orchestration: `main/finmitra/runner.py`
- Capacity input derivation: `main/finmitra/adapters.py`
- HTTP layer: `main/api_server.py`
- Capacity formulas: `main/components/profile/capacity/calculations.py`
- Capacity policies: `main/components/profile/common/config.py`
- Capacity schemas: `main/components/profile/common/schemas.py`

### Frontend

- Routing: `main/frontend/src/App.jsx`
- API client: `main/frontend/src/api.js`
- Assessment entry: `main/frontend/src/pages/Assess.jsx`
- Demo entry: `main/frontend/src/pages/Demo.jsx`
- Current result: `main/frontend/src/pages/Result.jsx`
- Capacity display: `main/frontend/src/components/assessment/CapacityCard.jsx`
- Shared UI primitives: `main/frontend/src/components/ui/`

### Existing authoritative result fields

Use the integrated result rather than deriving these again from transactions:

```text
profile.capacity.features.conservative_monthly_inflow
profile.capacity.features.essential_household_expense
profile.capacity.features.essential_business_expense
profile.capacity.features.existing_formal_emis
profile.capacity.features.existing_informal_installments
profile.capacity.features.monthly_surplus
profile.capacity.features.available_balance_buffer
profile.capacity.features.income_volatility
profile.capacity.features.safe_emi_max_factor
profile.capacity.safe_emi.minimum
profile.capacity.safe_emi.maximum
profile.capacity.requested_loan
profile.capacity.stress_tests
profile.repayment.new_credit_blocked
profile.repayment.status
profile.evidence.insufficient_history
profile.cashflow.status
profile.overall_confidence
```

---

## 4. MVP definition

### Required goal types

1. **Loan readiness**
2. **Savings target**

Loan readiness is the release-critical flow. Savings target is implemented after the loan engine is stable, using the same result contract.

### Required outcome states

```text
ACHIEVABLE_NOW
ACHIEVABLE_WITH_CHANGES
BLOCKED
INSUFFICIENT_DATA
INVALID_GOAL
```

### Required result sections

```text
goal
current_state
required_state
gap
paths
safety
assumptions
message_keys
```

### Explicit MVP exclusions

- Free-form AI parsing of goals.
- Personalized behavioral predictions.
- Automatic transaction/category editing.
- Loan approval claims.
- A recommendation to use the emergency/liquidity buffer as goal savings.
- Persistent saved plans.
- More than one simultaneous goal.
- Optimization across investments, tax, insurance, or lenders.

---

## 5. Recommended file structure

Create:

```text
main/
├── finmitra/
│   └── what_if/
│       ├── __init__.py
│       ├── schemas.py
│       ├── calculations.py
│       ├── engine.py
│       └── messages.py
├── tests/
│   ├── test_what_if_calculations.py
│   ├── test_what_if_engine.py
│   └── test_what_if_api.py
└── frontend/
    └── src/
        ├── pages/
        │   └── WhatIf.jsx
        └── components/
            └── what-if/
                ├── GoalTypeSelector.jsx
                ├── LoanGoalForm.jsx
                ├── SavingsGoalForm.jsx
                ├── GoalSummary.jsx
                ├── CurrentStateCard.jsx
                ├── GapCard.jsx
                ├── PathOptions.jsx
                ├── SafetyPanel.jsx
                └── AssumptionsPanel.jsx
```

`messages.py` should contain stable message-key constants or mappings, not localized prose. Actual translations belong to Person 3.

---

## 6. Domain model

### 6.1 Goal request schemas

Use a discriminated union rather than a single model containing many optional fields.

#### Loan goal

```python
class LoanReadinessGoal(BaseModel):
    type: Literal["LOAN_READINESS"]
    title: str
    target_amount: Decimal
    deadline_months: int
    annual_interest_rate: Decimal
    tenure_months: int
    desired_buffer: Decimal | None = None
```

Validation:

- `title`: trimmed, 1–80 characters.
- `target_amount`: greater than zero.
- `deadline_months`: 1–120 for the domain; the UI may offer a narrower recommended range.
- `annual_interest_rate`: 0–1 as a decimal, not percentage points.
- `tenure_months`: 1–360.
- `desired_buffer`: non-negative if supplied.

#### Savings goal

```python
class SavingsTargetGoal(BaseModel):
    type: Literal["SAVINGS_TARGET"]
    title: str
    target_amount: Decimal
    current_goal_savings: Decimal
    deadline_months: int
    conservative_contribution_factor: Decimal | None = None
```

Validation:

- Target amount is greater than zero.
- Current goal savings is non-negative.
- Deadline is 1–120 months.
- Contribution factor, if supported, is between 0 and 1 and must be returned as an explicit assumption.

### 6.2 Baseline schema

The calculation engine should not accept the entire untyped assessment dictionary. Introduce a typed, minimal baseline:

```python
class FinancialBaseline(BaseModel):
    borrower_id: str | None
    evaluation_date: date
    conservative_monthly_inflow: Decimal
    household_expense: Decimal
    business_expense: Decimal
    formal_emis: Decimal
    informal_installments: Decimal
    monthly_surplus: Decimal
    available_balance_buffer: Decimal
    safe_emi_min: Decimal
    safe_emi_max: Decimal
    safe_emi_max_factor: Decimal
    new_credit_blocked: bool
    repayment_status: str
    insufficient_history: bool
    cashflow_status: str
    overall_confidence: Decimal
    stress_tests: list[StressTestSummary]
```

Add one adapter function:

```python
baseline_from_assessment(result: dict[str, Any]) -> FinancialBaseline
```

This adapter is the only module allowed to know the nested assessment-result paths.

Validation rules:

- Monetary values must be finite and non-negative except `monthly_surplus`, which may be negative.
- `safe_emi_min <= safe_emi_max`.
- Safe EMI must be zero when `new_credit_blocked` is true.
- Factor must be in `(0, 1]`.
- Missing required authoritative values produces an insufficient-data result, not silent zero substitution.

### 6.3 Output schemas

Define typed models for:

- `GoalSnapshot`
- `CurrentState`
- `RequiredState`
- `FinancialGap`
- `PlanPath`
- `SafetySummary`
- `PlanAssumption`
- `WhatIfResult`

Recommended top-level response:

```python
class WhatIfResult(BaseModel):
    schema_version: Literal["1.0"]
    calculation_version: Literal["1.0"]
    outcome: WhatIfOutcome
    goal: GoalSnapshot
    current_state: CurrentState
    required_state: RequiredState
    gap: FinancialGap
    paths: list[PlanPath]
    safety: SafetySummary
    assumptions: list[PlanAssumption]
    message_keys: list[str]
```

Use numbers plus enums/message keys. Do not make English paragraphs the canonical result.

---

## 7. Numeric policy

### 7.1 Internal arithmetic

- Use `Decimal` for What If monetary and interest calculations.
- Convert existing floats using `Decimal(str(value))`, never `Decimal(value)`.
- Quantize currency outputs to two decimal places with a documented rounding mode.
- Only presentation code may round to whole rupees.
- Return API monetary values as JSON numbers after final quantization.

### 7.2 EMI parity

Do not create a different EMI implementation.

Preferred approach:

1. Extract or expose the existing capacity EMI helper through a stable integration boundary.
2. Add parity tests for zero and non-zero interest.
3. If cross-component import isolation prevents reuse, implement an identical local function with a prominent parity test against the capacity engine's output fixtures.

Formula for non-zero monthly rate:

```text
r = annual_interest_rate / 12
n = tenure_months
EMI = principal × r × (1 + r)^n / ((1 + r)^n - 1)
```

For zero interest:

```text
EMI = principal / tenure_months
```

### 7.3 Tolerances

- EMI parity: within ₹0.01.
- Path components versus gap: within ₹0.01.
- Percentage formatting is a frontend concern; the API retains decimal ratios.

---

## 8. Loan-readiness algorithm

Implement in this order.

### Step 1 — Validate baseline and goal

- Reject malformed goal fields through Pydantic.
- Treat missing baseline financial fields as `INSUFFICIENT_DATA`.
- Validate that all monetary values are finite.

### Step 2 — Apply hard safety precedence

If `new_credit_blocked` is true:

- Set outcome to `BLOCKED`.
- Preserve calculated EMI only as the goal requirement.
- Set feasible paths to an empty list or a single non-financial path of type `RESOLVE_REPAYMENT_BLOCK`.
- Do not return expense-reduction, income-increase, deadline-extension, or lower-principal paths as ways around the block.
- Include repayment status and the block message key in `safety`.

### Step 3 — Calculate required EMI

Use target amount, annual rate, and loan tenure.

### Step 4 — Compare with current safe capacity

```text
emi_gap = max(0, required_emi - safe_emi_max)
required_surplus = required_emi / safe_emi_max_factor
monthly_cashflow_gap = max(0, required_surplus - monthly_surplus)
```

Both gaps must be returned because they answer different questions:

- `emi_gap`: how much the desired EMI exceeds today's safe EMI ceiling.
- `monthly_cashflow_gap`: how much monthly surplus must improve under the active policy.

### Step 5 — Set outcome

- `ACHIEVABLE_NOW` when the required EMI is within safe capacity and no block/insufficient-data rule applies.
- `ACHIEVABLE_WITH_CHANGES` when the required EMI exceeds safe capacity and the baseline is otherwise valid.
- Stress-test failures do not automatically change an affordable plan to blocked; they appear prominently in safety warnings.

### Step 6 — Readiness deadline

The readiness deadline does not alter the EMI.

If no desired buffer is provided:

- Report the monthly cash-flow improvement to establish by the deadline.
- Do not divide that monthly improvement by deadline months.
- Do not claim that waiting alone makes an unaffordable recurring EMI affordable.

If a desired buffer is provided:

```text
buffer_gap = max(0, desired_buffer - available_balance_buffer)
monthly_buffer_contribution = buffer_gap / deadline_months
```

Return this separately from the recurring cash-flow gap.

### Step 7 — Generate paths

Required paths for `ACHIEVABLE_WITH_CHANGES`:

1. `REDUCE_EXPENSES`
   - Amount equals monthly cash-flow gap.
   - Never exceeds current household plus business expenses.
   - If it would exceed total expenses, mark the standalone path unavailable.

2. `INCREASE_INCOME`
   - Amount equals monthly cash-flow gap.
   - Clearly marked hypothetical.

3. `MIXED_CHANGE`
   - Default split: 50% expense reduction and 50% income increase, unless the expense side exceeds available expenses.
   - Components must sum to the gap.

4. `LOWER_PRINCIPAL`
   - Calculate affordable principal using `safe_emi_max`, the user's rate, and requested tenure.
   - Do not take the existing `max_principal` table unless tenure and rate match.

5. `EXTEND_LOAN_TENURE`
   - Search approved month increments up to the domain maximum for the shortest tenure at which EMI fits safe capacity.
   - Return unavailable if no tenure fits.

6. `BUILD_BUFFER`
   - Only present when the user supplied desired buffer or an existing zero-income stress test exposes a quantified buffer shortfall.

Do not offer `EXTEND_READINESS_DEADLINE` as a recurring-EMI solution. It may only reduce a separate buffer contribution.

---

## 9. Savings-target algorithm

### Step 1 — Validate explicit savings

`current_goal_savings` is a user-declared, goal-specific value. Do not substitute `available_balance_buffer`.

### Step 2 — Calculate target requirement

```text
remaining_target = max(0, target_amount - current_goal_savings)
required_monthly_saving = remaining_target / deadline_months
available_monthly_surplus = max(0, monthly_surplus)
monthly_gap = max(0, required_monthly_saving - available_monthly_surplus)
projected_amount = current_goal_savings + available_monthly_surplus × deadline_months
```

### Step 3 — Set outcome

- `ACHIEVABLE_NOW` if current goal savings already meet the target or monthly surplus can reach it by the deadline.
- `ACHIEVABLE_WITH_CHANGES` if a positive monthly gap exists.
- `INSUFFICIENT_DATA` if monthly surplus is not authoritative.
- A repayment block does not automatically block saving, but it must be shown as a safety warning and the plan must not encourage ignoring overdue obligations.

### Step 4 — Generate paths

- Reduce expenses by the monthly gap.
- Increase income by the monthly gap.
- Mixed change totaling the monthly gap.
- Extend deadline to the shortest month count that fits available surplus, when surplus is positive.
- Reduce target amount to projected amount at the current deadline.

### Step 5 — Safety wording contract

If the plan consumes 100% of monthly surplus, include a structured warning key indicating that no remaining monthly margin is modeled. Any conservative contribution factor must be policy-driven and explicit.

---

## 10. API integration plan

### 10.1 Core engine interface

The engine itself should be independent of HTTP:

```python
WhatIfEngine.plan(
    baseline: FinancialBaseline,
    goal: Goal,
) -> WhatIfResult
```

### 10.2 API endpoints

Use a short-lived, bounded server-side assessment store. Assessment responses include an opaque `assessment_id`; the primary planner resolves this ID to an immutable assessment snapshot.

#### JSON assessment path

```http
POST /api/what-if
```

Request:

```json
{
  "assessment_id": "opaque-server-issued-id",
  "goal": { "...": "LoanReadinessGoal or SavingsTargetGoal" }
}
```

Server flow:

```text
resolve immutable assessment by opaque ID
→ extract FinancialBaseline
→ run WhatIfEngine.plan()
→ return plan
```

#### Demo path

```http
POST /api/what-if/demo/{scenario}
```

Request body contains only the goal. Server rebuilds and assesses the selected demo before planning.

#### CSV path

```http
POST /api/what-if/csv
Content-Type: multipart/form-data
```

Accept the same file/context fields as `/api/assess/csv`, plus a JSON-encoded `goal` form field. Refactor the current CSV-to-`IntegratedBorrowerInput` assembly into a shared helper so assessment and What If cannot drift.

### 10.3 Why three paths are needed

Accepting client-edited input or result fields as authoritative would make repayment blocks and capacity limits easy to bypass. A process-local store provides an opaque, expiring trust boundary for the current single-server application; a durable shared store is required before multi-instance deployment.

For the current same-session frontend:

- Demo and CSV result routes keep the returned `assessment_id` in in-memory navigation state.
- Planning uses that ID while it remains valid; if the page is refreshed or the ID expires, explain that the assessment must be run again.
- Do not serialize CSV content into `localStorage`, URLs, or query parameters.

### 10.4 Error mapping

- Pydantic request validation: HTTP 422.
- Unknown demo: HTTP 400.
- Pipeline failure: HTTP 500 with no sensitive values.
- Structurally valid but insufficient baseline: HTTP 200 with `INSUFFICIENT_DATA`.
- Domain-invalid goal that escapes request validation: HTTP 200 with `INVALID_GOAL` only if it is a modeled product outcome; otherwise use 422 consistently.

Prefer 422 for malformed user input and reserve `INVALID_GOAL` for a valid shape that violates a financial/domain combination.

---

## 11. Frontend implementation plan

### 11.1 Route and entry

Add:

```text
/what-if
```

Entry behavior:

- From `Result.jsx`, add **Plan a goal**.
- Pass the current result source metadata:
  - Demo: scenario ID.
  - CSV: `File` plus form context.
- From global navigation, `/what-if` opens an empty state when no assessment source is available and links to Assess/Demos.

### 11.2 Page state machine

Use explicit states:

```text
NO_BASELINE
EDITING_GOAL
CALCULATING
SHOWING_RESULT
ERROR
```

Do not scatter multiple booleans that allow incompatible combinations.

### 11.3 Goal form

- Goal-type selector.
- Currency inputs stored as plain numeric strings while editing.
- Interest displayed as a percentage but converted to decimal before API submission.
- Separate readiness deadline and loan tenure fields with inline explanation.
- Validation summary and field-level messages.
- Disable submission during request.
- Preserve goal form values after API errors.

### 11.4 Result UI

Use existing `PageWrapper`, `Card`, `Button`, `Badge`, colors, radii, and typography.

Recommended order:

1. Outcome hero.
2. Goal summary.
3. “Where you are now” and “What is required” side-by-side on desktop.
4. Gap card with monthly values.
5. Potential path cards.
6. Safety panel.
7. Assumptions disclosure.
8. Actions: edit goal, return to assessment, secure share when Person 2 integration is ready.

### 11.5 Visual rules

- Do not communicate outcome by color alone.
- Use clear INR/month units on every recurring amount.
- Show deadline and loan tenure as different concepts.
- Avoid charts for one or two values; use labeled comparisons.
- If a bar visual is used, include exact text and handle values above the visual scale.
- Keep technical formula details behind an optional disclosure.

### 11.6 Localization readiness

Person 1 may use English fallback text during initial isolated development, but every canonical result must expose message keys and numeric parameters.

Do not:

- Concatenate sentences from fragments.
- Embed formatted currency in backend messages.
- Put financial values inside translation keys.
- Make logic depend on displayed text.

---

## 12. Message-key handoff to Person 3

Deliver a machine-readable inventory containing at least:

```text
whatIf.outcome.achievableNow
whatIf.outcome.achievableWithChanges
whatIf.outcome.blocked
whatIf.outcome.insufficientData
whatIf.goal.loanReadiness
whatIf.goal.savingsTarget
whatIf.current.monthlySurplus
whatIf.current.safeEmi
whatIf.required.emi
whatIf.required.monthlySavings
whatIf.gap.emi
whatIf.gap.cashflow
whatIf.gap.buffer
whatIf.path.reduceExpenses
whatIf.path.increaseIncome
whatIf.path.mixedChange
whatIf.path.lowerPrincipal
whatIf.path.extendLoanTenure
whatIf.path.extendSavingsDeadline
whatIf.path.buildBuffer
whatIf.path.resolveRepaymentBlock
whatIf.safety.repaymentBlocked
whatIf.safety.highStressFailure
whatIf.safety.lowConfidence
whatIf.safety.noRemainingMargin
whatIf.assumption.safeEmiPolicy
whatIf.assumption.userDeclaredSavings
whatIf.assumption.interestRate
whatIf.assumption.noApprovalGuarantee
```

For each key, provide:

- Required parameters.
- Parameter type and unit.
- Standard English fallback.
- Simple English fallback.
- Where the key appears.

---

## 13. Shareable-field handoff to Person 2

Person 1 should approve this minimal allowlist for a shared What If summary:

```text
schema_version
calculation_version
outcome
goal.type
goal.title (optional and user-approved)
goal.target_amount
goal.deadline_months
goal.annual_interest_rate (loan only)
goal.tenure_months (loan only)
required_state.required_emi OR required_monthly_saving
gap.monthly_cashflow_gap OR monthly_savings_gap
safety.new_credit_blocked
```

Exclude:

- Full current-state income/expense breakdown by default.
- Raw assessment response.
- Stress-test details.
- Borrower ID.
- Transaction or source information.
- Free-form metadata.

Person 2 should consume an explicit serializer from Person 1 or an agreed schema, not select fields ad hoc from the UI state.

---

## 14. Test plan

### 14.1 Calculation unit tests

Loan:

- Zero-interest EMI.
- Normal-interest EMI.
- EMI exactly equal to safe capacity.
- EMI one paisa above capacity.
- Negative monthly surplus.
- Safe EMI factor at supported boundaries.
- Desired buffer already met.
- Desired buffer shortfall divided across deadline.
- Deadline change does not change EMI.
- Lower-principal inverse calculation.
- Shortest viable extended tenure.
- No viable tenure within maximum.
- Mixed path components equal gap.

Savings:

- Goal already funded.
- Goal reachable exactly at deadline.
- Positive monthly gap.
- Zero monthly surplus.
- Negative monthly surplus.
- Deadline extension calculation.
- Current goal savings greater than target.
- Available buffer is not used as current goal savings.

Safety:

- Repayment block takes precedence over affordability.
- Blocked loan exposes no financial workaround paths.
- Thin history returns insufficient data.
- Missing nested assessment fields are not silently zeroed.
- Non-finite values are rejected.

### 14.2 Capacity parity tests

Use several principals, rates, and tenures, including:

```text
₹40,000 at 14% for 12 months
₹1,00,000 at 0% for 10 months
₹1,00,000 at 14% for 24 months
₹5,00,000 at 18% for 60 months
```

What If EMI must match the existing capacity loan assessment within ₹0.01.

### 14.3 API tests

- Strong demo affordable goal.
- Strong demo unaffordable goal.
- Unpaid demo blocked goal.
- Thin demo insufficient-data goal.
- Unknown demo.
- Malformed goal type.
- Missing loan field.
- Percentage accidentally supplied as `14` instead of `0.14`.
- CSV loan plan.
- CSV savings plan.
- Pipeline error sanitization.

### 14.4 Frontend tests

- Empty state without assessment.
- Goal-type field switching.
- Percentage-to-decimal conversion.
- Loading and double-submit prevention.
- API error with preserved form.
- Correct outcome component.
- All recurring values show `/month`.
- Deadline and tenure are distinct.
- Blocked state hides change paths.
- Keyboard navigation and accessible error association.

### 14.5 Regression commands

From `main/`:

```powershell
python -m pytest tests/test_integrated_pipeline.py -q
python -m pytest tests/test_what_if_calculations.py tests/test_what_if_engine.py tests/test_what_if_api.py -q
```

From `main/frontend/`:

```powershell
npm run build
```

Run the full repository verification before handoff when the environment has all declared API dependencies.

---

## 15. Ordered implementation milestones

### Milestone 0 — Contract review

Checklist:

- [ ] Confirm Person 1 owns both loan and savings MVP flows.
- [ ] Confirm shared-file integrator.
- [ ] Confirm goal deadline and tenure bounds.
- [ ] Confirm Decimal/rounding policy.
- [ ] Confirm structured result and message-key format with Person 3.
- [ ] Confirm shareable allowlist with Person 2.

Exit criterion: schemas and examples accepted before UI work.

### Milestone 1 — Domain schemas and baseline adapter

Checklist:

- [ ] Create `finmitra/what_if/` package.
- [ ] Add goal discriminated union.
- [ ] Add baseline and output schemas.
- [ ] Add assessment-to-baseline adapter.
- [ ] Add schema validation tests.
- [ ] Document field provenance.

Exit criterion: strong, unpaid, and thin assessment fixtures convert deterministically.

### Milestone 2 — Loan calculation engine

Checklist:

- [ ] Implement Decimal helpers and EMI calculation/reuse.
- [ ] Implement block and insufficient-data precedence.
- [ ] Implement gap calculations.
- [ ] Implement buffer contribution.
- [ ] Implement scenario generators.
- [ ] Add capacity parity tests.
- [ ] Add full loan boundary test matrix.

Exit criterion: engine returns stable structured results for all three demos and parity tests pass.

### Milestone 3 — Savings calculation engine

Checklist:

- [ ] Implement goal-specific savings logic.
- [ ] Ensure buffer is never silently used.
- [ ] Implement savings scenarios.
- [ ] Implement no-remaining-margin warning.
- [ ] Add savings boundary tests.

Exit criterion: funded, exactly reachable, gap, zero-surplus, and negative-surplus cases pass.

### Milestone 4 — API integration

Checklist:

- [ ] Extract reusable CSV input assembly helper.
- [ ] Add JSON What If endpoint.
- [ ] Add demo What If endpoint.
- [ ] Add CSV What If endpoint.
- [ ] Map validation/errors consistently.
- [ ] Add endpoint tests.
- [ ] Update API documentation/readme.

Exit criterion: all goal types work through authoritative server-side assessment paths.

### Milestone 5 — Frontend goal flow

Checklist:

- [ ] Add What If API client functions.
- [ ] Add route and empty state.
- [ ] Add goal-type selector and forms.
- [ ] Pass demo/CSV source metadata from result.
- [ ] Implement page state machine.
- [ ] Implement result cards and paths.
- [ ] Implement edit/recalculate flow.
- [ ] Verify responsive and keyboard behavior.

Exit criterion: user can complete strong, blocked, and insufficient-data flows without raw JSON editing.

### Milestone 6 — Cross-workstream handoff

Checklist:

- [ ] Freeze schema/calculation version 1.0.
- [ ] Deliver message-key inventory and parameter map to Person 3.
- [ ] Deliver shareable serializer/allowlist to Person 2.
- [ ] Add fixtures for every outcome.
- [ ] Confirm localization never needs to parse English.
- [ ] Confirm QR owner never needs the full assessment result.

Exit criterion: Persons 2 and 3 can integrate using fixtures without importing calculation internals.

### Milestone 7 — Release verification

Checklist:

- [ ] Run existing pipeline regressions.
- [ ] Run all What If tests.
- [ ] Run frontend build.
- [ ] Verify INR/percentage/month units.
- [ ] Verify no guarantee/approval wording.
- [ ] Verify original assessment is never mutated.
- [ ] Verify no raw transaction data enters What If output.
- [ ] Review high-value and extreme-input behavior.
- [ ] Complete financial calculation review.

Exit criterion: Definition of done is satisfied and shared integrator approves merge.

---

## 16. Suggested commit sequence

Keep commits independently reviewable:

1. `feat(what-if): add typed goal and result contracts`
2. `feat(what-if): extract financial baseline from assessments`
3. `feat(what-if): implement loan readiness calculations`
4. `test(what-if): add EMI parity and loan boundary coverage`
5. `feat(what-if): implement savings target planning`
6. `feat(api): add authoritative what-if endpoints`
7. `feat(ui): add what-if goal forms and result view`
8. `test(ui): cover what-if states and accessibility`
9. `docs(what-if): publish localization and sharing contracts`

Avoid mixing dependency upgrades or unrelated visual refactors into these commits.

---

## 17. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Frontend cannot reconstruct authoritative assessment after refresh | User must repeat upload | Keep original File only in current session; show clear reselect flow; do not persist statement data |
| What If EMI drifts from capacity engine | Conflicting advice | Reuse helper where feasible and enforce parity tests |
| Readiness deadline is confused with loan tenure | Incorrect user understanding | Separate fields, labels, help text, result sections, and tests |
| Buffer is treated as spendable savings | Unsafe recommendation | Require explicit goal savings; keep buffer separate in schemas and UI |
| Expense reduction exceeds actual expenses | Impossible path | Cap/check standalone path and mark unavailable |
| Hard block is accidentally bypassed | Safety/policy failure | Make block first engine branch and add regression tests |
| Thin-file missing values become zero | False precision | Typed baseline validation; return insufficient data |
| English prose becomes API contract | Localization blocked | Return enums, message keys, parameters, and numeric fields |
| Shared files conflict with Persons 2/3 | Merge delays | Dedicated directories, small integration commits, designated integrator |
| Float rounding creates inconsistent rupee gaps | User sees totals that do not add up | Decimal arithmetic and explicit tolerance tests |

---

## 18. Person 1 definition of done

Person 1's work is complete when:

- Loan readiness and savings target produce deterministic structured plans.
- Results use the real integrated FinMitra baseline.
- EMI calculations match the existing capacity engine.
- Current state, required state, gap, paths, safety, and assumptions are all present.
- Hard blocks cannot be bypassed.
- Thin or missing data never becomes false zero-value certainty.
- Deadline and tenure have correct, distinct effects.
- Buffer and goal savings remain separate.
- The frontend works for demo and CSV assessment sources in the current session.
- Person 3 has stable message keys and typed parameters.
- Person 2 has a minimal explicit share allowlist.
- Existing pipeline tests and frontend build remain green.
- No approval guarantee or regulated-advice claim is introduced.

---

## 19. Immediate first tasks

Person 1 should begin with these five actions:

1. Review the PRD and resolve the contract questions in Milestone 0.
2. Create the `finmitra/what_if` package and discriminated goal schemas.
3. Build `FinancialBaseline` and `baseline_from_assessment()` using strong, unpaid, and thin demo fixtures.
4. Add EMI parity tests before implementing scenario generation.
5. Share the draft output JSON fixture with Persons 2 and 3 before starting the final UI.
