from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.ml.bsr_predictor import bsr_to_sales, BSRPredictor

router = APIRouter(prefix="/prediction", tags=["prediction"])


class SalesEstimateResponse(BaseModel):
    bsr: int
    genre: str
    daily_estimated: float
    monthly_estimated: int
    lower_bound: int
    upper_bound: int
    error_range_pct: int
    note: str


class SimulationRequest(BaseModel):
    genre: str
    keyword: str
    target_bsr: int


class SimulationResponse(BaseModel):
    genre: str
    keyword: str
    target_bsr: int
    monthly_sales: SalesEstimateResponse
    feasibility: str
    recommendation: str


@router.get("/bsr-to-sales", response_model=SalesEstimateResponse)
async def bsr_to_sales_estimate(
    bsr: Annotated[int, Query(ge=1, le=10_000_000)],
    genre: str = "default",
):
    """
    BSR → 推定月間販売数を計算する。
    ※推定値（±20%誤差）/ 実測販売データ非公開のため
    """
    estimate = bsr_to_sales(bsr, genre)
    return SalesEstimateResponse(
        bsr=estimate.bsr,
        genre=estimate.genre,
        daily_estimated=estimate.daily_estimated,
        monthly_estimated=estimate.monthly_estimated,
        lower_bound=estimate.lower_bound,
        upper_bound=estimate.upper_bound,
        error_range_pct=estimate.error_range_pct,
        note=estimate.note,
    )


@router.post("/simulate", response_model=SimulationResponse)
async def simulate(req: SimulationRequest):
    """
    ジャンル + 目標BSR → 月間売上・実現可能性をシミュレーションする。
    """
    estimate = bsr_to_sales(req.target_bsr, req.genre)

    # 実現可能性判定
    if req.target_bsr <= 1_000:
        feasibility = "高難度"
        recommendation = f"BSR {req.target_bsr:,}は上位0.1%。競合分析と差別化が必須です。"
    elif req.target_bsr <= 10_000:
        feasibility = "中難度"
        recommendation = f"BSR {req.target_bsr:,}は達成可能な目標です。キーワードSEOと表紙最適化を重視してください。"
    elif req.target_bsr <= 50_000:
        feasibility = "低難度"
        recommendation = f"BSR {req.target_bsr:,}はニッチジャンルで十分到達可能です。"
    else:
        feasibility = "容易"
        recommendation = "まずはBSR 50,000以内を目標にしましょう。"

    return SimulationResponse(
        genre=req.genre,
        keyword=req.keyword,
        target_bsr=req.target_bsr,
        monthly_sales=SalesEstimateResponse(
            bsr=estimate.bsr,
            genre=estimate.genre,
            daily_estimated=estimate.daily_estimated,
            monthly_estimated=estimate.monthly_estimated,
            lower_bound=estimate.lower_bound,
            upper_bound=estimate.upper_bound,
            error_range_pct=estimate.error_range_pct,
            note=estimate.note,
        ),
        feasibility=feasibility,
        recommendation=recommendation,
    )
