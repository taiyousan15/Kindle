from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.collectors.autocomplete_client import AutocompleteClient
from src.collectors.merchantwords_client import MerchantWordsClient
from src.core.config import get_settings
from src.db.database import get_db
from src.db.models import KeywordAnalysis

router = APIRouter(prefix="/keywords", tags=["keywords"])
log = structlog.get_logger()


class SearchVolumeResponse(BaseModel):
    estimated: int
    confidence: int  # 1〜3
    note: str
    merchant_words: int | None = None
    autocomplete_score: float | None = None


class KeywordAnalysisResponse(BaseModel):
    keyword: str
    search_volume: SearchVolumeResponse
    competition: str | None
    book_count: int | None
    avg_bsr: int | None
    trend: str | None
    related_keywords: list[str]
    top_asins: list[str]


class SuggestionsResponse(BaseModel):
    keyword: str
    suggestions: list[str]
    autocomplete_score: float
    note: str


@router.get("/search", response_model=list[KeywordAnalysisResponse])
async def search_keywords(
    q: Annotated[str, Query(min_length=1, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    db: AsyncSession = Depends(get_db),
):
    """キーワード検索（DBキャッシュ優先 → 未分析の場合リアルタイム取得）。"""
    stmt = (
        select(KeywordAnalysis)
        .where(KeywordAnalysis.keyword.ilike(f"%{q}%"))
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    return [_to_response(r) for r in records]


@router.get("/{keyword}/analysis", response_model=KeywordAnalysisResponse)
async def get_keyword_analysis(
    keyword: str,
    db: AsyncSession = Depends(get_db),
):
    """
    特定キーワードの詳細分析を返す。
    DBに存在しない場合はリアルタイムで分析して保存する。
    """
    stmt = select(KeywordAnalysis).where(KeywordAnalysis.keyword == keyword)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        record = await _analyze_and_save(keyword, db)

    return _to_response(record)


@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    seed: Annotated[str, Query(min_length=1, max_length=100)],
    count: Annotated[int, Query(ge=1, le=20)] = 10,
):
    """Amazon Autocomplete APIからキーワード候補を取得する。"""
    client = AutocompleteClient()
    result = await client.get_suggestions(seed, count)

    return SuggestionsResponse(
        keyword=seed,
        suggestions=result.suggestions,
        autocomplete_score=result.autocomplete_score,
        note=result.note,
    )


async def _analyze_and_save(
    keyword: str,
    db: AsyncSession,
) -> KeywordAnalysis:
    """リアルタイムでキーワードを分析してDBに保存する。"""
    settings = get_settings()

    autocomplete = AutocompleteClient()
    ac_result = await autocomplete.get_suggestions(keyword)

    mw_result = None
    if settings.merchantwords_api_key:
        mw_client = MerchantWordsClient(settings.merchantwords_api_key)
        mw_result = await mw_client.get_volume(keyword)

    # 検索ボリューム合算
    sources = 0
    sv_parts = []
    note_parts = []

    if ac_result.autocomplete_score > 0:
        sources += 1
        ac_volume = autocomplete.calculate_volume_estimate(ac_result.autocomplete_score)
        sv_parts.append(ac_volume)
        note_parts.append("Autocomplete")

    if mw_result and mw_result.search_volume > 0:
        sources += 1
        sv_parts.append(mw_result.search_volume)
        note_parts.append("MerchantWords")

    sv_estimated = round(sum(sv_parts) / len(sv_parts)) if sv_parts else 0
    note = f"推定値 / {' + '.join(note_parts)}合算" if note_parts else "推定値 / データ不足"

    record = KeywordAnalysis(
        keyword=keyword,
        sv_merchant_words=mw_result.search_volume if mw_result else None,
        sv_autocomplete_score=ac_result.autocomplete_score,
        sv_estimated=sv_estimated,
        sv_confidence=min(3, sources),
        sv_note=note,
        related_keywords=ac_result.suggestions[:10],
    )
    db.add(record)
    await db.flush()

    log.info("keyword_analyzed", keyword=keyword, sv_estimated=sv_estimated, confidence=sources)
    return record


def _to_response(record: KeywordAnalysis) -> KeywordAnalysisResponse:
    stars = record.sv_confidence or 1
    return KeywordAnalysisResponse(
        keyword=record.keyword,
        search_volume=SearchVolumeResponse(
            estimated=record.sv_estimated,
            confidence=stars,
            note=record.sv_note or "推定値",
            merchant_words=record.sv_merchant_words,
            autocomplete_score=float(record.sv_autocomplete_score) if record.sv_autocomplete_score else None,
        ),
        competition=record.competition,
        book_count=record.book_count,
        avg_bsr=record.avg_bsr,
        trend=record.trend,
        related_keywords=record.related_keywords or [],
        top_asins=record.top_asins or [],
    )
