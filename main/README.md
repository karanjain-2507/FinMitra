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
