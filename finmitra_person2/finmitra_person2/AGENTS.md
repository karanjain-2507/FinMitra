# Person 2 guardrails

Work only on the FinMitra cash-flow intelligence engine.

- Person 2 owns the primary trained cash-flow ML model.
- Do not implement evidence ingestion, repayment logic, debt capacity, final readiness, or loan approval.
- Respect Person 1's `model_eligible` flag.
- Never treat unverified self-declared income, transfers, refunds, or loan disbursements as operating revenue.
- Preserve temporal ordering and prevent future leakage.
- Scores are 0–100. Confidence is 0–1. Missing values are `None` unless zero has real meaning.
- Random seed is 42. Models and features must be versioned.
- Training and inference must call the same feature pipeline.
- Run the full tests and CLI fixtures before declaring completion.
