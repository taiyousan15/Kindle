"""BSR予測モデルの単体テスト。"""
from datetime import datetime, timedelta

import pytest

from src.ml.bsr_predictor import BSRPredictor, SalesEstimate, bsr_to_sales


class TestBsrToSales:
    def test_returns_sales_estimate(self):
        result = bsr_to_sales(1000, "ビジネス・経済")
        assert isinstance(result, SalesEstimate)

    def test_higher_bsr_means_lower_sales(self):
        low_bsr = bsr_to_sales(100, "default")
        high_bsr = bsr_to_sales(100_000, "default")
        assert low_bsr.monthly_estimated > high_bsr.monthly_estimated

    def test_error_range_always_20(self):
        result = bsr_to_sales(5000)
        assert result.error_range_pct == 20

    def test_bounds_are_correct(self):
        result = bsr_to_sales(5000)
        assert result.lower_bound == round(result.monthly_estimated * 0.8)
        assert result.upper_bound == round(result.monthly_estimated * 1.2)

    def test_genre_coefficient_affects_sales(self):
        manga = bsr_to_sales(5000, "マンガ")      # coeff=1.30
        default = bsr_to_sales(5000, "default")  # coeff=1.00
        assert manga.monthly_estimated > default.monthly_estimated

    def test_unknown_genre_falls_back_to_default(self):
        result = bsr_to_sales(5000, "存在しないジャンル")
        default = bsr_to_sales(5000, "default")
        assert result.monthly_estimated == default.monthly_estimated

    def test_zero_bsr_returns_zero(self):
        result = bsr_to_sales(0)
        assert result.monthly_estimated == 0

    def test_note_contains_estimated(self):
        result = bsr_to_sales(1000)
        assert "推定値" in result.note

    @pytest.mark.parametrize("bsr,genre", [
        (100, "ビジネス・経済"),
        (1_000, "自己啓発"),
        (5_000, "コンピュータ・IT"),
        (20_000, "マンガ"),
        (100_000, "default"),
    ])
    def test_bsr_ranges(self, bsr, genre):
        result = bsr_to_sales(bsr, genre)
        assert result.monthly_estimated >= 0
        assert result.lower_bound <= result.monthly_estimated <= result.upper_bound


class TestBSRPredictor:
    def _make_history(self, n: int = 30, start_bsr: int = 5000) -> list[tuple[datetime, int]]:
        base = datetime.utcnow() - timedelta(days=n)
        return [(base + timedelta(days=i), max(1, start_bsr - i * 50)) for i in range(n)]

    def test_returns_none_for_insufficient_data(self):
        predictor = BSRPredictor()
        result = predictor.predict("B00TEST001", [(datetime.utcnow(), 5000)])
        assert result is None

    def test_trend_predict_rising(self):
        predictor = BSRPredictor()
        # BSRが下がる（= 順位上昇 = rising）
        history = self._make_history(30, start_bsr=10_000)
        result = predictor.predict("B00TEST001", history)
        assert result is not None
        assert result.trend == "rising"

    def test_trend_predict_declining(self):
        predictor = BSRPredictor()
        # BSRが上がる（= 順位下降 = declining）
        base = datetime.utcnow() - timedelta(days=30)
        history = [(base + timedelta(days=i), 1000 + i * 200) for i in range(30)]
        result = predictor.predict("B00TEST001", history)
        assert result is not None
        assert result.trend == "declining"

    def test_prediction_has_bounds(self):
        predictor = BSRPredictor()
        history = self._make_history(30)
        result = predictor.predict("B00TEST001", history)
        assert result is not None
        assert result.lower_bound_30d <= result.predicted_bsr_30d
        assert result.predicted_bsr_30d <= result.upper_bound_30d

    def test_prediction_bsr_positive(self):
        predictor = BSRPredictor()
        history = self._make_history(30)
        result = predictor.predict("B00TEST001", history)
        assert result is not None
        assert result.predicted_bsr_7d >= 1
        assert result.predicted_bsr_30d >= 1
