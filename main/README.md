# FinMitra integrated pipeline

This folder preserves all four team submissions under `components/` and connects
their real engines through explicit JSON adapters. Person 4's mocks are not used
by the integrated runner.

## Run it

From this folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe .\run_finmitra.py
```

This opens the interactive demo menu. The JSON-output commands remain available:

```powershell
.\.venv\Scripts\python.exe .\run_finmitra.py --demo strong --pretty
.\.venv\Scripts\python.exe .\run_finmitra.py --demo unpaid --pretty
.\.venv\Scripts\python.exe .\run_finmitra.py --demo thin --pretty
```

Save a result:

```powershell
.\.venv\Scripts\python.exe .\run_finmitra.py --demo unpaid --pretty --output .\results\unpaid.json
```

Run your own canonical input:

```powershell
.\.venv\Scripts\python.exe .\run_finmitra.py --input borrower.json --pretty
```

The input contract is defined in `finmitra/schemas.py`. It combines Person 1's
raw `sources`, Person 3's `informal_loans` and `repayment_claims`, and only the
household/request fields that cannot be responsibly inferred from transactions.
Business inflow, business expense, volatility, delinquent exposure, and informal
installments are derived by the pipeline.

## Real flow

1. Person 1 ingests, normalizes, deduplicates, validates, and grades evidence.
2. The adapter converts that canonical transaction timeline to Person 2's schema.
3. Person 2 calculates the locked 12 features and estimates the probability of
   cash-flow stress in the next 90 days using the v2 classifier. It also exposes
   `100 × (1 − stress_probability)` as a compatibility health score for fusion.
4. The same normalized timeline plus declared loans feeds Person 3.
5. Person 3 can hard-block new credit for materially unpaid obligations.
6. Person 4 calculates safe EMI and assembles the final profile.

Important integration corrections include deterministic cutoff dates, field-name
mapping, provenance-shape mapping, paise-to-INR conversion, repayment-ID aliasing,
real upstream results instead of mocks, and correct `None` handling for thin-file
cash-flow assessments.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe .\verify_all.py
```

The first command runs the new end-to-end integration regressions. The second
runs those plus all preserved component tests. See `REVIEW.md` for the
integration fixes and the limitations that remain before any bank-facing use.

## What If planning

The What If module uses the completed four-engine assessment as an immutable
baseline and works backward from either a loan-readiness goal or a savings
target. It returns structured current-state, required-state, gap, path, safety,
and assumption fields; localized presentation can consume the stable message
keys without parsing English prose.

The API exposes authoritative planning paths for each current input mode:

```text
POST /api/what-if
POST /api/what-if/demo/{scenario}
POST /api/what-if/csv
POST /api/passports
GET  /api/passports/{credential_id}
POST /api/passports/verify
```

Assessment endpoints issue a short-lived opaque ID, and the planner resolves it
to an immutable server-owned result rather than trusting client-edited financial
inputs or derived fields. In the frontend, open a completed result and
select **Plan a Goal**, or use the **What If** navigation item to see the
assessment-first entry flow.

## Financial Passport

Completed assessments can issue a 30-day, selectively disclosed financial
passport. The server derives every claim from its immutable assessment snapshot,
uses a pseudonymous subject identifier, and signs the canonical credential with
HMAC-SHA256. Credentials disclose categorical evidence, cash-flow, repayment,
readiness, confidence, and stress-check claims—not borrower IDs, transaction
history, balances, income, or exact Safe EMI values.

An optional What If goal can be supplied during issuance. The server recomputes
the plan and discloses only goal type, outcome, and deadline; goal title and amount
remain private. The `/passport` and `/verifier` routes provide issuance and manual
verification flows based on the attached Stitch concept. Camera QR decoding is not
claimed or simulated in this web build.

Set `FINMITRA_PASSPORT_SIGNING_KEY` in deployed environments. The development
fallback key and credential registry are process-local, so production deployment
requires managed key storage and a shared durable credential registry.
