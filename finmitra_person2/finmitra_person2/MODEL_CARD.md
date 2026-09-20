# Model card: FinMitra Cash-Flow Intelligence v1

## Purpose

Estimate the health and stability of a small business's cash flow from normalized, borrower-permissioned transaction evidence.

## Intended use

Decision support for a lender/NBFC analyst or another FinMitra component. The output is not a repayment probability, bureau score, affordability calculation, approval, or rejection.

## Training data

Training data is synthetic for hackathon demonstration and does not establish real-world predictive validity. Nine simulated archetypes generate transaction-level histories. The same feature code processes synthetic training records and inference inputs.

## Target

Each row uses up to 24 months before cutoff. The next three months produce a 0–100 target:

`35% surplus-margin score + 25% inflow-stability score + 20% positive-net-month rate + 20% net-trend score`.

The target is clamped to 0–100. It is cash-flow health, not default or repayment behavior.

## Model and baseline

The primary estimator is scikit-learn `HistGradientBoostingRegressor`, chosen for nonlinear tabular relationships and deterministic, fast inference. A mean `DummyRegressor` is the mandatory baseline. MAE, RMSE, and R² for validation/test are saved in `artifacts/metadata_v1.json`.

## Validation

Borrowers are split 70/15/15, and no borrower appears in more than one split. Within every row the feature window ends before the target window begins. Automated tests add post-cutoff transactions and verify historical features remain unchanged.

## Explainability

Global permutation importance is saved with the artifact. Local reasons use one-feature-at-a-time sensitivity against training medians. These explanations describe model sensitivity, not causation.

## Confidence and unfamiliar data

Confidence combines active months, eligible operating transaction count, corroboration, coverage, and the fraction of features outside training 1st–99th percentiles. Unfamiliar inputs produce warnings and may be degraded. Insufficient inputs receive no score.

## Limitations

- Synthetic performance is not evidence of performance on real borrowers.
- Source categorization quality depends on Person 1.
- Three target months are a short horizon.
- The simulator cannot reproduce every region, industry, shock, or cash practice.
- Training-distribution checks are simple marginal checks, not a full multivariate drift detector.
- Real deployment requires representative consented data, governance review, calibration, monitoring, and lender validation.
