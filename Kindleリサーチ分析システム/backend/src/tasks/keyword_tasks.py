import asyncio

import structlog
from celery import shared_task

from src.core.config import get_settings

log = structlog.get_logger()

# 定期更新対象のベースキーワード
BASE_KEYWORDS = [
    "AI活用", "ChatGPT", "生成AI", "Claude", "プロンプト",
    "新NISA", "オルカン", "米国株", "インデックス投資",
    "節税", "手取り最大化", "副業",
    "防災", "備蓄", "サバイバル",
    "発達障害", "ADHD", "仕事術",
    "男性育休", "職場交渉",
    "Kindle出版", "KDP", "電子書籍",
    "セルフパブリッシング", "個人出版",
]


@shared_task(
    name="src.tasks.keyword_tasks.refresh_keywords",
    max_retries=2,
    default_retry_delay=300,
)
def refresh_keywords() -> dict:
    """キーワードの検索ボリューム・関連キーワードを定期更新する。"""
    settings = get_settings()
    return asyncio.run(_refresh_async(settings))


async def _refresh_async(settings) -> dict:
    from src.collectors.autocomplete_client import AutocompleteClient
    from src.collectors.merchantwords_client import MerchantWordsClient
    from src.db.database import AsyncSessionLocal
    from src.db.models import KeywordAnalysis
    from sqlalchemy import select
    from datetime import datetime, timezone, timedelta

    autocomplete = AutocompleteClient()
    mw_client = MerchantWordsClient(settings.merchantwords_api_key) if settings.merchantwords_api_key else None

    success_count = 0
    error_count = 0

    async with AsyncSessionLocal() as session:
        for keyword in BASE_KEYWORDS:
            try:
                ac_result = await autocomplete.get_suggestions(keyword)

                mw_result = None
                if mw_client:
                    mw_result = await mw_client.get_volume(keyword)

                # ボリューム合算
                sources = 0
                sv_parts = []
                note_parts = []

                if ac_result.autocomplete_score > 0:
                    sources += 1
                    sv_parts.append(autocomplete.calculate_volume_estimate(ac_result.autocomplete_score))
                    note_parts.append("Autocomplete")

                if mw_result and mw_result.search_volume > 0:
                    sources += 1
                    sv_parts.append(mw_result.search_volume)
                    note_parts.append("MerchantWords")

                sv_estimated = round(sum(sv_parts) / len(sv_parts)) if sv_parts else 0
                note = f"推定値 / {' + '.join(note_parts)}合算" if note_parts else "推定値 / データ不足"

                # UPSERT
                stmt = select(KeywordAnalysis).where(KeywordAnalysis.keyword == keyword)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record is None:
                    record = KeywordAnalysis(keyword=keyword)
                    session.add(record)

                record.sv_merchant_words = mw_result.search_volume if mw_result else None
                record.sv_autocomplete_score = ac_result.autocomplete_score
                record.sv_estimated = sv_estimated
                record.sv_confidence = min(3, sources)
                record.sv_note = note
                record.related_keywords = ac_result.suggestions[:10]
                record.sv_updated_at = datetime.now(timezone.utc)

                success_count += 1

            except Exception as e:
                log.error("keyword_refresh_failed", keyword=keyword, error=str(e))
                error_count += 1

        await session.commit()

    log.info("keyword_refresh_complete", success=success_count, errors=error_count)
    return {"success_count": success_count, "error_count": error_count}
