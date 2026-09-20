# Repayment Engine (Person 3)

Deterministic reconstruction of loan schedules and repayment status.

```python
from common.schemas import BorrowerInput
from repayment.engine import assess

result = assess(borrower_profile)
```

Person 4 can later consume:

- `result.score`
- `result.status`
- `result.confidence`
- `result.new_credit_blocked`
- `result.hard_cap`
- `result.features`
- `result.reasons`

This package depends only on `common`. It does not import Person 1, 2, or 4 internals.

Cash-flow fields, if present on `BorrowerInput`, are ignored for status and score.

```bash
python run_repayment.py --input fixtures/strong_borrower.json
python -m unittest repayment.test_engine
```
