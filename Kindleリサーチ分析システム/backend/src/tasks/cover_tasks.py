import asyncio

import structlog
from celery import shared_task

from src.core.config import get_settings

log = structlog.get_logger()


@shared_task(name="src.tasks.cover_tasks.analyze_pending_covers")
def analyze_pending_covers() -> dict:
    """未分析の表紙をバッチ処理する（コスト制御: 10枚/実行）。"""
    settings = get_settings()
    return asyncio.run(_analyze_async(settings))


async def _analyze_async(settings) -> dict:
    from src.analyzers.cover_analyzer import CoverAnalyzer
    from src.db.database import AsyncSessionLocal
    from src.db.models import KindleBook, BookCover
    from sqlalchemy import select

    analyzer = CoverAnalyzer(settings.anthropic_api_key)
    batch_size = settings.cover_analysis_batch_size

    async with AsyncSessionLocal() as session:
        # 表紙URLがあるが分析未済の書籍を取得
        stmt = (
            select(KindleBook)
            .where(
                KindleBook.cover_image_url.isnot(None),
            )
            .outerjoin(BookCover, KindleBook.asin == BookCover.asin)
            .where(BookCover.asin.is_(None))
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        books = result.scalars().all()

        if not books:
            return {"count": 0, "message": "No pending covers"}

        success_count = 0
        for book in books:
            try:
                analysis = await analyzer.analyze(book.cover_image_url, book.asin)
                cover = BookCover(
                    asin=book.asin,
                    image_url=book.cover_image_url,
                    primary_colors=analysis.primary_colors,
                    font_style=analysis.font_style,
                    layout=analysis.layout,
                    mood=analysis.mood,
                    analysis_json=analysis.raw_json,
                    ctr_score=analysis.ctr_score,
                )
                session.add(cover)
                success_count += 1
            except Exception as e:
                log.error("cover_analysis_failed", asin=book.asin, error=str(e))

        await session.commit()

    return {"count": success_count}
