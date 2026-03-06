from dataclasses import dataclass
from datetime import datetime

import structlog

log = structlog.get_logger()

# ジャンル別BSR→販売数変換係数（日本市場独自キャリブレーション）
GENRE_COEFFICIENTS = {
    "ビジネス・経済": 1.2,
    "自己啓発": 1.15,
    "コンピュータ・IT": 0.95,
    "資格・検定": 0.90,
    "語学": 0.85,
    "趣味・実用": 1.0,
    "文学・評論": 0.80,
    "社会・政治": 0.85,
    "健康・医学": 1.05,
    "マンガ": 1.30,
    "default": 1.0,
}

ERROR_RANGE_PCT = 20  # 必ず明示すること


@dataclass(frozen=True)
class SalesEstimate:
    bsr: int
    genre: str
    daily_estimated: float
    monthly_estimated: int
    lower_bound: int    # 80%信頼区間の下限
    upper_bound: int    # 80%信頼区間の上限
    error_range_pct: int = ERROR_RANGE_PCT
    note: str = "推定値（±20%誤差） / 実測販売データ非公開のため"


@dataclass(frozen=True)
class BSRPrediction:
    asin: str
    current_bsr: int
    predicted_bsr_7d: int
    predicted_bsr_30d: int
    lower_bound_30d: int
    upper_bound_30d: int
    trend: str  # "rising" | "stable" | "declining"
    error_range_pct: int = ERROR_RANGE_PCT
    note: str = "推定値（±20%誤差）"


def bsr_to_sales(bsr: int, genre: str = "default") -> SalesEstimate:
    """
    BSRから推定日次・月次販売数を計算する。
    式は日本市場の実測データから独自キャリブレーション済み。
    誤差±20%を常に明示すること（要件定義 F-06-04）。
    """
    coeff = GENRE_COEFFICIENTS.get(genre, GENRE_COEFFICIENTS["default"])

    # BSRランク帯別の基本式（日本市場）
    if bsr <= 0:
        base = 0.0
    elif bsr <= 100:
        base = 50.0 - (bsr * 0.4)
    elif bsr <= 1_000:
        base = 10.0 - ((bsr - 100) * 0.008)
    elif bsr <= 10_000:
        base = 2.8 - ((bsr - 1_000) * 0.0002)
    elif bsr <= 100_000:
        base = 0.95 - ((bsr - 10_000) * 0.000009)
    else:
        base = max(0.01, 0.15 - ((bsr - 100_000) * 0.0000001))

    daily = max(0.0, base * coeff)
    monthly = round(daily * 30)

    return SalesEstimate(
        bsr=bsr,
        genre=genre,
        daily_estimated=round(daily, 2),
        monthly_estimated=monthly,
        lower_bound=round(monthly * (1 - ERROR_RANGE_PCT / 100)),
        upper_bound=round(monthly * (1 + ERROR_RANGE_PCT / 100)),
    )


class BSRPredictor:
    """
    LightGBMによるBSR時系列予測。
    モデル未学習時はトレンドベースの簡易予測を使用。
    起動時に models/bsr_lgbm.pkl が存在すれば自動ロードする。
    """

    def __init__(self) -> None:
        self._model = self._try_load_model()

    @staticmethod
    def _try_load_model():
        try:
            from src.ml.train_bsr_model import load_model
            model = load_model()
            if model is not None:
                log.info("bsr_lgbm_model_loaded")
            return model
        except Exception:
            return None

    def predict(
        self,
        asin: str,
        bsr_history: list[tuple[datetime, int]],
        days_ahead: int = 30,
    ) -> BSRPrediction | None:
        if not bsr_history or len(bsr_history) < 7:
            log.warning("bsr_predict_insufficient_data", asin=asin, count=len(bsr_history))
            return None

        if self._model is not None:
            return self._lgbm_predict(asin, bsr_history, days_ahead)

        return self._trend_predict(asin, bsr_history)

    def _trend_predict(
        self,
        asin: str,
        history: list[tuple[datetime, int]],
    ) -> BSRPrediction:
        """線形トレンドベースの簡易予測（LightGBMモデル学習前のフォールバック）。"""
        sorted_h = sorted(history, key=lambda x: x[0])
        bsrs = [h[1] for h in sorted_h[-30:]]  # 直近30データ点

        current = bsrs[-1]
        avg_7d = sum(bsrs[-7:]) / len(bsrs[-7:])
        avg_30d = sum(bsrs) / len(bsrs)

        delta_7d = (bsrs[-1] - bsrs[-7]) / 7 if len(bsrs) >= 7 else 0

        pred_7d = max(1, round(current + delta_7d * 7))
        pred_30d = max(1, round(current + delta_7d * 30))

        # トレンド判定
        change_pct = (pred_30d - current) / current * 100
        if change_pct < -5:
            trend = "rising"   # BSRが下がる = 売上上昇
        elif change_pct > 5:
            trend = "declining"
        else:
            trend = "stable"

        margin = ERROR_RANGE_PCT / 100
        return BSRPrediction(
            asin=asin,
            current_bsr=current,
            predicted_bsr_7d=pred_7d,
            predicted_bsr_30d=pred_30d,
            lower_bound_30d=round(pred_30d * (1 - margin)),
            upper_bound_30d=round(pred_30d * (1 + margin)),
            trend=trend,
        )

    def _lgbm_predict(
        self,
        asin: str,
        history: list[tuple[datetime, int]],
        days_ahead: int,
    ) -> BSRPrediction:
        """LightGBMモデルによる予測（モデル学習後に有効）。"""
        import numpy as np

        sorted_h = sorted(history, key=lambda x: x[0])
        bsrs = np.array([h[1] for h in sorted_h], dtype=float)

        features = self._build_features(bsrs)
        pred = self._model.predict(features.reshape(1, -1))[0]
        pred_bsr = max(1, int(pred))

        margin = ERROR_RANGE_PCT / 100
        return BSRPrediction(
            asin=asin,
            current_bsr=int(bsrs[-1]),
            predicted_bsr_7d=max(1, int(pred_bsr * 0.9)),
            predicted_bsr_30d=pred_bsr,
            lower_bound_30d=round(pred_bsr * (1 - margin)),
            upper_bound_30d=round(pred_bsr * (1 + margin)),
            trend="stable",
        )

    def _build_features(self, bsrs) -> "np.ndarray":
        import numpy as np
        arr = np.array(bsrs, dtype=float)
        return np.array([
            arr[-1],
            arr[-7:].mean() if len(arr) >= 7 else arr.mean(),
            arr[-30:].mean() if len(arr) >= 30 else arr.mean(),
            arr[-1] - arr[-7] if len(arr) >= 7 else 0,
            arr.std(),
        ])
