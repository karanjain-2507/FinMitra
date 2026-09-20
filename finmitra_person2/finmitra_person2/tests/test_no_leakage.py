from dataclasses import replace
from datetime import date, timedelta

from features.pipeline import build_features_for_profile
from schemas import BorrowerInput


def test_post_cutoff_transaction_does_not_change_features(stable_profile):
    baseline = build_features_for_profile(stable_profile)
    future = replace(
        stable_profile.transactions[0], transaction_id="FUTURE",
        date=(date.fromisoformat(stable_profile.as_of_date) + timedelta(days=40)).isoformat(),
        amount_paise=999999999,
    )
    changed = BorrowerInput(stable_profile.borrower_id, stable_profile.as_of_date, stable_profile.transactions + (future,))
    result = build_features_for_profile(changed)
    assert result.values == baseline.values
    assert result.context["future_transaction_count"] == 1


def test_cutoff_change_controls_visibility(stable_profile):
    last = max(stable_profile.transactions, key=lambda item: item.date)
    before = (date.fromisoformat(last.date) - timedelta(days=1)).isoformat()
    earlier = BorrowerInput(stable_profile.borrower_id, before, stable_profile.transactions)
    assert build_features_for_profile(earlier).context["future_transaction_count"] >= 1
