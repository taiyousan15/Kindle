from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.analyzers.cover_analyzer import CoverAnalyzer
from src.core.config import get_settings
from src.core.llm_client import LLMClient
from src.db.database import get_db
from src.db.models import BookCover

router = APIRouter(prefix="/covers", tags=["covers"])


class CoverTrendItem(BaseModel):
    asin: str
    image_url: str
    primary_colors: list[str]
    font_style: str | None
    layout: str | None
    mood: str | None
    ctr_score: int | None


class CoverAnalyzeRequest(BaseModel):
    image_url: str
    asin: str = "TEMP"


class CoverAnalyzeResponse(BaseModel):
    asin: str
    primary_colors: list[str]
    font_style: str
    layout: str
    mood: str
    ctr_score: int
    analysis_text: str


@router.get("/trends", response_model=list[CoverTrendItem])
async def get_cover_trends(
    genre: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
):
    """ジャンル別の表紙傾向を返す（分析済み書籍のみ）。"""
    stmt = select(BookCover).limit(limit)
    result = await db.execute(stmt)
    covers = result.scalars().all()

    return [
        CoverTrendItem(
            asin=c.asin,
            image_url=c.image_url,
            primary_colors=c.primary_colors or [],
            font_style=c.font_style,
            layout=c.layout,
            mood=c.mood,
            ctr_score=c.ctr_score,
        )
        for c in covers
    ]


@router.post("/analyze", response_model=CoverAnalyzeResponse)
async def analyze_cover(req: CoverAnalyzeRequest):
    """表紙画像URLをClaude Visionで分析する。"""
    settings = get_settings()
    analyzer = CoverAnalyzer(LLMClient(settings))
    result = await analyzer.analyze(req.image_url, req.asin)

    return CoverAnalyzeResponse(
        asin=result.asin,
        primary_colors=result.primary_colors,
        font_style=result.font_style,
        layout=result.layout,
        mood=result.mood,
        ctr_score=result.ctr_score,
        analysis_text=result.analysis_text,
    )
