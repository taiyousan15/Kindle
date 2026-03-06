"""
LightGBMによるBSR時系列予測モデルの学習スクリプト。

使用方法:
    cd backend
    .venv/bin/python -m src.ml.train_bsr_model --output models/bsr_lgbm.pkl

必要データ: bsr_history テーブルに最低30日分の蓄積が必要。
"""
import argparse
import asyncio
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import structlog

log = structlog.get_logger()

MODEL_DIR = Path(__file__).parent.parent.parent / "models"


def build_features(bsrs: np.ndarray) -> np.ndarray:
    """BSR時系列からLightGBM用の特徴量ベクトルを構築する。"""
    n = len(bsrs)
    return np.array([
        bsrs[-1],                                          # 最新BSR
        bsrs[-7:].mean() if n >= 7 else bsrs.mean(),      # 7日平均
        bsrs[-14:].mean() if n >= 14 else bsrs.mean(),    # 14日平均
        bsrs[-30:].mean() if n >= 30 else bsrs.mean(),    # 30日平均
        bsrs[-1] - bsrs[-7] if n >= 7 else 0,             # 7日変化量
        bsrs[-1] - bsrs[-14] if n >= 14 else 0,           # 14日変化量
        bsrs.std(),                                        # 標準偏差
        bsrs.min(),                                        # 最小BSR
        bsrs.max(),                                        # 最大BSR
        (bsrs[-1] - bsrs[0]) / max(1, len(bsrs)),         # 線形トレンドスロープ
    ])


async def load_training_data() -> tuple[np.ndarray, np.ndarray]:
    """DBからBSR時系列を読み込んで (X, y) ペアを生成する。"""
    from sqlalchemy import select, text

    from src.db.database import AsyncSessionLocal
    from src.db.models.bsr_history import BSRHistory

    X_list: list[np.ndarray] = []
    y_list: list[float] = []

    since = datetime.utcnow() - timedelta(days=365)

    async with AsyncSessionLocal() as session:
        # ASIN一覧取得
        stmt = text(
            "SELECT DISTINCT asin FROM bsr_history "
            "WHERE recorded_at >= :since "
            "GROUP BY asin HAVING count(*) >= 37"
        )
        result = await session.execute(stmt, {"since": since})
        asins = [row[0] for row in result.fetchall()]

        log.info("training_data_asins", count=len(asins))

        for asin in asins:
            hist_stmt = (
                select(BSRHistory)
                .where(BSRHistory.asin == asin, BSRHistory.recorded_at >= since)
                .order_by(BSRHistory.recorded_at.asc())
            )
            rows = (await session.execute(hist_stmt)).scalars().all()
            bsrs = np.array([r.bsr for r in rows], dtype=float)

            # ウィンドウ = 30日、ラベル = 7日後のBSR
            for i in range(30, len(bsrs) - 7):
                window = bsrs[i - 30:i]
                target = bsrs[i + 7]
                X_list.append(build_features(window))
                y_list.append(target)

    if not X_list:
        raise RuntimeError("学習データが不足しています（最低30日分のBSR蓄積が必要）。")

    X = np.vstack(X_list)
    y = np.array(y_list, dtype=float)
    log.info("training_data_ready", samples=len(y))
    return X, y


def train(X: np.ndarray, y: np.ndarray, output_path: Path) -> None:
    """LightGBMモデルを学習してpickleに保存する。"""
    import lightgbm as lgb
    from sklearn.model_selection import train_test_split

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    params = {
        "objective": "regression",
        "metric": "rmse",
        "num_leaves": 63,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
    }

    dtrain = lgb.Dataset(X_train, label=y_train)
    dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)

    callbacks = [lgb.early_stopping(50, verbose=True), lgb.log_evaluation(50)]
    model = lgb.train(
        params,
        dtrain,
        num_boost_round=500,
        valid_sets=[dval],
        callbacks=callbacks,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(model, f)

    val_preds = model.predict(X_val)
    rmse = np.sqrt(((val_preds - y_val) ** 2).mean())
    log.info("model_trained", rmse=round(rmse, 1), output=str(output_path))


def load_model(model_path: Path | None = None):
    """保存済みモデルをロードする。存在しない場合はNoneを返す。"""
    path = model_path or MODEL_DIR / "bsr_lgbm.pkl"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


async def main(output: str) -> None:
    X, y = await load_training_data()
    train(X, y, Path(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BSR予測モデルを学習する")
    parser.add_argument(
        "--output",
        default=str(MODEL_DIR / "bsr_lgbm.pkl"),
        help="モデル保存パス",
    )
    args = parser.parse_args()
    asyncio.run(main(args.output))
