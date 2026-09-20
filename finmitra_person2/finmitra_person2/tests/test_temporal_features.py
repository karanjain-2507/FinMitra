from features.seasonality import seasonality_features
from features.trends import normalized_trend, recent_change
import pandas as pd


def test_trend_direction():
    assert normalized_trend(pd.Series([1, 2, 3, 4])) > 0
    assert normalized_trend(pd.Series([4, 3, 2, 1])) < 0


def test_recent_change_is_bounded_and_directional():
    assert 0 < recent_change(pd.Series([10, 10, 10, 20, 20, 20])) <= 2
    assert -2 <= recent_change(pd.Series([20, 20, 20, 10, 10, 10])) < 0


def test_predictable_seasonality_detected():
    pattern = pd.Series([10, 20, 60, 100, 60, 20, 10, 15, 40, 80, 40, 15] * 2)
    assert seasonality_features(pattern)["seasonality_strength"] > .9


def test_flat_series_not_called_seasonal():
    assert seasonality_features(pd.Series([50] * 24))["seasonality_strength"] == 0
