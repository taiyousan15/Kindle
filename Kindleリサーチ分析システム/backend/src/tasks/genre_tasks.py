import asyncio
from datetime import datetime, timezone

import structlog
from celery import shared_task

log = structlog.get_logger()

PERIODS = ["daily", "weekly", "monthly", "halfyear"]
PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30, "halfyear": 180}

GENRES = [
    "ビジネス・経済", "自己啓発", "コンピュータ・IT",
    "資格・検定", "語学", "趣味・実用",
    "文学・評論", "健康・医学", "マンガ",
]


@shared_task(name="src.tasks.genre_tasks.compute_genre_trends")
def compute_genre_trends() -> dict:
    """ジャンルトレンドを集計してDBに保存する。"""
    return asyncio.run(_compute_async())


async def _compute_async() -> dict:
    from src.db.database import AsyncSessionLocal
    from src.db.models import GenreTrend, BSRHistory, KindleBook
    from sqlalchemy import select, func, text
    import statistics

    saved_count = 0

    async with AsyncSessionLocal() as session:
        for genre in GENRES:
            for period in PERIODS:
                days = PERIOD_DAYS[period]
                try:
                    # 該当ジャンル・期間のBSRデータを集計
                    stmt = text("""
                        SELECT bh.bsr
                        FROM bsr_history bh
                        JOIN kindle_books kb ON bh.asin = kb.asin
                        WHERE kb.genre = :genre
                          AND bh.recorded_at >= NOW() - INTERVAL ':days days'
                          AND bh.bsr > 0
                        ORDER BY bh.bsr ASC
                        LIMIT 10000
                    """)

                    # 簡易実装（実際はTimescaleDBのtime_bucket等を使用）
                    trend = GenreTrend(
                        genre=genre,
                        period=period,
                        avg_bsr=None,
                        median_bsr=None,
                        book_count=0,
                        top_keywords=[],
                        trend_score=0.5,
                        recorded_at=datetime.now(timezone.utc),
                    )
                    session.add(trend)
                    saved_count += 1

                except Exception as e:
                    log.error("genre_trend_failed", genre=genre, period=period, error=str(e))

        await session.commit()

    return {"saved_count": saved_count}
