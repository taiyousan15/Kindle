import asyncio
from datetime import datetime, timezone

import structlog
from celery import shared_task

from src.collectors.keepa_client import KeepaClient
from src.core.config import get_settings
from src.ml.bsr_predictor import bsr_to_sales

log = structlog.get_logger()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="src.tasks.bsr_tasks.update_bsr_batch",
)
def update_bsr_batch(self, asins: list[str] | None = None) -> dict:
    """BSR履歴を一括更新するCeleryタスク。"""
    settings = get_settings()

    if not settings.keepa_api_key:
        log.warning("bsr_update_skipped", reason="keepa_api_key_not_set")
        return {"skipped": True, "reason": "KEEPA_API_KEY not configured"}

    try:
        client = KeepaClient(settings.keepa_api_key)

        # ASINリストが未指定の場合はDB上位1000件を取得
        target_asins = asins or _get_tracked_asins()

        if not target_asins:
            return {"success": True, "count": 0}

        # 100件ずつバッチ処理
        success_count = 0
        error_count = 0
        batches = [target_asins[i:i+100] for i in range(0, len(target_asins), 100)]

        for batch in batches:
            try:
                books = client.get_bsr_history(batch, days=7)
                records = asyncio.run(_save_bsr_records(books))
                success_count += len(records)
            except Exception as e:
                log.error("bsr_batch_error", error=str(e))
                error_count += len(batch)

        log.info("bsr_update_complete", success=success_count, errors=error_count)
        return {
            "success": True,
            "success_count": success_count,
            "error_count": error_count,
        }

    except Exception as exc:
        log.error("bsr_update_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _save_bsr_records(books) -> list:
    """BSRレコードをDBに保存する（async）。"""
    from src.db.database import AsyncSessionLocal
    from src.db.models import BSRHistory

    saved = []
    async with AsyncSessionLocal() as session:
        for book in books:
            for record in book.bsr_history[-24:]:  # 直近24件
                sales = bsr_to_sales(record.bsr)
                bsr_row = BSRHistory(
                    asin=book.asin,
                    bsr=record.bsr,
                    category=record.category,
                    recorded_at=record.recorded_at,
                    estimated_daily_sales=int(sales.daily_estimated),
                    data_source="keepa",
                )
                session.add(bsr_row)
                saved.append(bsr_row)
        await session.commit()

    return saved


def _get_tracked_asins() -> list[str]:
    """DBから追跡対象のASINリストを取得する。"""
    return asyncio.run(_fetch_asins_from_db())


async def _fetch_asins_from_db() -> list[str]:
    from sqlalchemy import select, text
    from src.db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT asin FROM kindle_books ORDER BY updated_at DESC LIMIT 1000")
        )
        return [row[0] for row in result.fetchall()]
