from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import GenreTrend

router = APIRouter(prefix="/genres", tags=["genres"])
log = structlog.get_logger()

Period = Literal["daily", "weekly", "monthly", "halfyear"]

# サポートするジャンル一覧（amazon.co.jp Kindle Store）
SUPPORTED_GENRES = [
    "ビジネス・経済",
    "自己啓発",
    "コンピュータ・IT",
    "資格・検定",
    "語学",
    "趣味・実用",
    "文学・評論",
    "社会・政治",
    "健康・医学",
    "マンガ",
    "教育・学参",
    "旅行・アウトドア",
    "料理・グルメ",
    "美容・ファッション",
]


class GenreTrendResponse(BaseModel):
    genre: str
    period: str
    avg_bsr: int | None
    median_bsr: int | None
    book_count: int | None
    top_keywords: list[str]
    target_demo: str | None
    trend_score: float | None
    recorded_at: str


@router.get("", response_model=list[str])
async def list_genres():
    """サポートするジャンル一覧を返す。"""
    return SUPPORTED_GENRES


@router.get("/{genre}/trend", response_model=list[GenreTrendResponse])
async def get_genre_trend(
    genre: str,
    period: Annotated[Period, Query()] = "monthly",
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    ジャンルのトレンドデータを返す。
    period: daily | weekly | monthly | halfyear
    """
    stmt = (
        select(GenreTrend)
        .where(GenreTrend.genre == genre, GenreTrend.period == period)
        .order_by(GenreTrend.recorded_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    return [
        GenreTrendResponse(
            genre=r.genre,
            period=r.period,
            avg_bsr=r.avg_bsr,
            median_bsr=r.median_bsr,
            book_count=r.book_count,
            top_keywords=r.top_keywords or [],
            target_demo=r.target_demo,
            trend_score=float(r.trend_score) if r.trend_score else None,
            recorded_at=r.recorded_at.isoformat(),
        )
        for r in records
    ]


@router.get("/compare", response_model=dict[str, GenreTrendResponse | None])
async def compare_genres(
    genres: Annotated[str, Query(description="カンマ区切り、最大5ジャンル")],
    period: Annotated[Period, Query()] = "monthly",
    db: AsyncSession = Depends(get_db),
):
    """最大5ジャンルを横断比較する。"""
    genre_list = [g.strip() for g in genres.split(",")][:5]

    result = {}
    for genre in genre_list:
        stmt = (
            select(GenreTrend)
            .where(GenreTrend.genre == genre, GenreTrend.period == period)
            .order_by(GenreTrend.recorded_at.desc())
            .limit(1)
        )
        r = await db.execute(stmt)
        record = r.scalar_one_or_none()

        if record:
            result[genre] = GenreTrendResponse(
                genre=record.genre,
                period=record.period,
                avg_bsr=record.avg_bsr,
                median_bsr=record.median_bsr,
                book_count=record.book_count,
                top_keywords=record.top_keywords or [],
                target_demo=record.target_demo,
                trend_score=float(record.trend_score) if record.trend_score else None,
                recorded_at=record.recorded_at.isoformat(),
            )
        else:
            result[genre] = None

    return result
