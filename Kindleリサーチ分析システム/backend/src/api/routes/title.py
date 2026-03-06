from fastapi import APIRouter
from pydantic import BaseModel

from src.analyzers.title_analyzer import TitleAnalyzer
from src.core.config import get_settings

router = APIRouter(prefix="/title", tags=["title"])


class TitleAnalyzeRequest(BaseModel):
    title: str
    genre: str = "一般"
    bestseller_titles: list[str] = []


class TitleAnalyzeResponse(BaseModel):
    original_title: str
    score: int
    length_chars: int
    has_number: bool
    has_benefit: bool
    has_target: bool
    structure: str
    improvements: list[str]
    generated_titles: list[str]
    analysis: str


@router.post("/analyze", response_model=TitleAnalyzeResponse)
async def analyze_title(req: TitleAnalyzeRequest):
    """タイトルを分析してスコアと改善案を返す。"""
    settings = get_settings()
    analyzer = TitleAnalyzer(settings.anthropic_api_key)
    result = await analyzer.analyze(
        title=req.title,
        genre=req.genre,
        bestseller_titles=req.bestseller_titles,
    )
    return TitleAnalyzeResponse(
        original_title=result.original_title,
        score=result.score,
        length_chars=result.length_chars,
        has_number=result.has_number,
        has_benefit=result.has_benefit,
        has_target=result.has_target,
        structure=result.structure,
        improvements=result.improvements,
        generated_titles=result.generated_titles,
        analysis=result.analysis,
    )
