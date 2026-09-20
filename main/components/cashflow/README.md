# FinMitra Person 2 — Cash-Flow Intelligence Engine

FinMitra is an evidence and decision-support layer for lenders evaluating small businesses with fragmented financial histories. It does not replace lender underwriting. The original “AI credit score” concept was split into evidence, cash flow, repayment, and capacity engines so every output has a defensible meaning.

This standalone project owns only the primary trained cash-flow model. Person 1 provides normalized and verified transactions. Person 2 estimates business cash-flow health. Person 3 handles repayment. Person 4 handles affordability and profile assembly.

## What this project does

- Generates transaction-level synthetic histories for nine business archetypes.
- Builds temporal, stability, trend, seasonality, recency, concentration, and evidence-context features.
- Predicts a forward-looking 0–100 cash-flow health target.
- Compares gradient boosting against a mean baseline using MAE, RMSE, and R².
- Produces global permutation importance and local model-sensitivity reasons.
- Returns confidence and explicit sufficient/degraded/insufficient status.
- Exposes the 25th-percentile `conservative_monthly_inflow` in paise for Person 4.

It does not predict default, score repayment, calculate safe EMI, approve/reject a loan, normalize raw bank documents, or compute FinMitra's final readiness.

## Data flow

```text
Person 1 NormalizedTransaction[]
        -> eligibility and cutoff filtering
        -> one versioned feature pipeline
        -> cash-flow health model
        -> CashflowResult for Person 4
```

Transactions marked `model_eligible=false`, future records, failed/reversed entries, and duplicate IDs cannot strengthen operating features. Unverified self-declared cash is reported as context but excluded from verified revenue. Transfers, refunds, and loan disbursements are not operating income. Household spending remains outside the core business cash-flow calculation.

## Target and leakage prevention

Features use up to 24 historical months. The following three months produce the synthetic target:

```text
35% future operating-surplus margin
25% future inflow stability
20% positive operating-net month rate
20% future operating-net trend
```

The result is clamped to 0–100. Feature code receives the cutoff explicitly, and leakage tests prove post-cutoff transactions do not change historical features.

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

On macOS/Linux use `.venv/bin/python`.

## Generate, train, and test

```bash
python generate_dataset.py
python train.py
python -m pytest -v
```

Generated bulk data is ignored by Git. Versioned model artifacts and metadata live in `artifacts/`. Existing artifacts are backed up with timestamps before retraining.

## CLI

```bash
python run_cashflow.py --input fixtures/stable_kirana/input.json --pretty
python run_cashflow.py --input fixtures/seasonal_farmer/input.json --pretty
python run_cashflow.py --input fixtures/growing_business/input.json --pretty
python run_cashflow.py --input fixtures/declining_business/input.json --pretty
python run_cashflow.py --input fixtures/thin_file/input.json --pretty
```

Successful stdout is JSON only; errors/logs go to stderr.

## Public Python interface

```python
from model.inference import CashflowEngine
from schemas import BorrowerInput

profile = BorrowerInput.from_dict(payload)
result = CashflowEngine().assess(profile)
```

See `CONTRACT.md` for exact fields, eligibility, units, status semantics, reason codes, and Person 4 handoff.

## Interpretation

`score` is estimated business cash-flow health/stability. `confidence` describes how well the available evidence supports that assessment. Neither is a loan decision or default probability. Local reasons are model-sensitivity explanations, not causal claims.

## Limitations

Training data is synthetic for hackathon demonstration and does not establish real-world predictive validity. Production use requires representative consented data, outcome validation, fairness/governance review, recalibration, drift monitoring, and lender oversight. See `MODEL_CARD.md`.
