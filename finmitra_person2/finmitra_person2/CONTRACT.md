# Cash-flow engine contract

## Input

`BorrowerInput` contains `borrower_id`, an ISO `as_of_date`, and a list of normalized transactions from Person 1. Amounts are integer paise. Required transaction fields are defined in `schemas.py`.

Only successful records dated on or before the cutoff and marked `model_eligible=true` enter model features. Duplicate IDs are counted and ignored after the first occurrence. An anomaly flag is contextual and does not by itself exclude a valid record.

Operating inflows are `BUSINESS_INCOME`, `MARKETPLACE_SETTLEMENT`, `POS_SETTLEMENT`, and `SUPPORTED_CASH_SALES`. Operating outflows are the versioned categories in `config.py`. Transfers, refunds, loan flows, household expenses, and unsupported cash declarations do not become operating revenue or expense.

## Output

`CashflowResult` contains:

- `component="cashflow"`
- `version`: model version
- `score`: estimated future cash-flow health from 0–100, or `null`
- `status`: `SUFFICIENT`, `DEGRADED`, or `INSUFFICIENT`
- `confidence`: assessment support from 0–1, distinct from the score
- `features`: lender-readable cash-flow facts
- `reasons`: `CFxx` model-sensitivity explanations
- `warnings`: limitations such as out-of-distribution input

`features.conservative_monthly_inflow` is the 25th percentile of eligible monthly operating inflow, in paise, and is the required Person 4 handoff.

## Status policy

- Fewer than 3 active operating months or 30 eligible operating transactions: `INSUFFICIENT`, `score=null`.
- At least 6 active months, 60 operating transactions, 70% month coverage, and acceptable training support: `SUFFICIENT`.
- Other scorable cases: `DEGRADED`.

## Versioning

Feature version and model version are both `1.0.0`. A different feature order requires a feature-version bump and retraining.

## Reason codes

`CF01` stable inflows; `CF02` weak stability; `CF03` positive surplus; `CF04` negative surplus; `CF05` improving trend; `CF06` deteriorating trend; `CF07` volatility; `CF08` predictable seasonality; `CF09` unstable seasonality; `CF10` strong recent cash flow; `CF11` weak recent cash flow; `CF12` expense burden; `CF13` low resilience; `CF14` insufficient history; `CF15` low coverage; `CF16` corroborated history; `CF17` evidence constraint; `CF18` other positive sensitivity; `CF19` other negative sensitivity.
