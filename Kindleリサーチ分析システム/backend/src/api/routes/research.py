"""
無料リサーチエンジン API ルート

POST /api/research/        - フルリサーチ実行
POST /api/research/keywords - キーワード展開のみ
GET  /api/research/sources  - 利用可能ソース一覧
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ...core.config import Settings, get_settings
from ...collectors.free_research import FreeResearchEngine
from ...collectors.keyword_expander import KeywordExpander

router = APIRouter(prefix="/api/research", tags=["research"])


# ------------------------------------------------------------------
# リクエスト / レスポンス スキーマ
# ------------------------------------------------------------------

class ResearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    sources: list[str] | None = Field(
        default=None,
        description="収集ソース（省略時は全て）: search, trends, social, video, academic, books, news, qa",
    )


class KeywordExpandRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)


class SearchResultOut(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    is_overseas: bool


class ResearchResponse(BaseModel):
    keyword: str
    bucket_a_count: int
    bucket_b_count: int
    bucket_c_count: int
    total_sources: int
    bucket_a: list[SearchResultOut]
    bucket_b: list[SearchResultOut]
    bucket_c: list[dict]
    keywords_expanded: list[str]
    trends: dict
    youtube_data: list[dict]
    news: list[dict]


class KeywordExpandResponse(BaseModel):
    seed: str
    single: list[str]
    related: list[str]
    compound: list[str]
    english: list[str]
    total: int


class SourceInfo(BaseModel):
    name: str
    category: str
    is_overseas: bool
    method: str
    cost: str


# ------------------------------------------------------------------
# エンドポイント
# ------------------------------------------------------------------

@router.post("/", response_model=ResearchResponse)
async def run_research(
    body: ResearchRequest,
    settings: Settings = Depends(get_settings),
) -> ResearchResponse:
    """
    指定キーワードで全無料ソースからリサーチを実行。

    - bucket_a: 海外情報（翻訳してそのまま台本に活用可）
    - bucket_b: 日本情報（テーマ・トレンド把握のみ）
    - bucket_c: 学術・統計データ（引用可）
    """
    engine = FreeResearchEngine(settings)
    result = await engine.research(body.keyword, sources=body.sources)

    return ResearchResponse(
        keyword=result.keyword,
        bucket_a_count=len(result.bucket_a),
        bucket_b_count=len(result.bucket_b),
        bucket_c_count=len(result.bucket_c),
        total_sources=result.total_sources,
        bucket_a=[
            SearchResultOut(
                title=r.title,
                url=r.url,
                snippet=r.snippet,
                source=r.source,
                is_overseas=r.is_overseas,
            )
            for r in result.bucket_a[:30]
        ],
        bucket_b=[
            SearchResultOut(
                title=r.title,
                url=r.url,
                snippet=r.snippet,
                source=r.source,
                is_overseas=r.is_overseas,
            )
            for r in result.bucket_b[:30]
        ],
        bucket_c=result.bucket_c[:20],
        keywords_expanded=result.keywords_expanded,
        trends=result.trends,
        youtube_data=result.youtube_data[:10],
        news=result.news[:20],
    )


@router.post("/keywords", response_model=KeywordExpandResponse)
async def expand_keywords(
    body: KeywordExpandRequest,
    settings: Settings = Depends(get_settings),
) -> KeywordExpandResponse:
    """
    キーワードを単体・関連・複合・英語に展開する。
    Ollama + Google/Bing/Yahoo Suggest を使用（全て無料）。
    """
    expander = KeywordExpander(settings)
    tree = await expander.expand(body.keyword)
    return KeywordExpandResponse(**tree.to_dict())


@router.get("/sources", response_model=list[SourceInfo])
async def list_sources() -> list[SourceInfo]:
    """利用可能な全リサーチソース一覧を返す"""
    return [
        # 検索エンジン
        SourceInfo(name="DuckDuckGo", category="search", is_overseas=True, method="scraping", cost="¥0"),
        SourceInfo(name="Google Suggest", category="keywords", is_overseas=False, method="api_free", cost="¥0"),
        SourceInfo(name="Bing Autosuggest", category="keywords", is_overseas=False, method="api_free", cost="¥0"),
        SourceInfo(name="Yahoo Japan Suggest", category="keywords", is_overseas=False, method="api_free", cost="¥0"),
        # トレンド
        SourceInfo(name="Google Trends", category="trends", is_overseas=False, method="pytrends", cost="¥0"),
        SourceInfo(name="HackerNews", category="trends", is_overseas=True, method="api_free", cost="¥0"),
        SourceInfo(name="Yahoo Realtime", category="trends", is_overseas=False, method="scraping", cost="¥0"),
        SourceInfo(name="ProductHunt", category="trends", is_overseas=True, method="scraping", cost="¥0"),
        # SNS
        SourceInfo(name="X (Twitter)", category="social", is_overseas=False, method="cookie_auth", cost="¥0"),
        SourceInfo(name="note", category="social", is_overseas=False, method="api+scraping", cost="¥0"),
        SourceInfo(name="Reddit", category="social", is_overseas=True, method="api_free", cost="¥0"),
        # 動画
        SourceInfo(name="YouTube", category="video", is_overseas=True, method="api_free_10k/day", cost="¥0"),
        SourceInfo(name="YouTube Captions", category="video", is_overseas=True, method="transcript_api", cost="¥0"),
        # 学術
        SourceInfo(name="Wikipedia (ja)", category="academic", is_overseas=False, method="api_free", cost="¥0"),
        SourceInfo(name="Wikipedia (en)", category="academic", is_overseas=True, method="api_free", cost="¥0"),
        SourceInfo(name="ArXiv", category="academic", is_overseas=True, method="api_free", cost="¥0"),
        SourceInfo(name="PubMed", category="academic", is_overseas=True, method="api_free", cost="¥0"),
        SourceInfo(name="Semantic Scholar", category="academic", is_overseas=True, method="api_free", cost="¥0"),
        SourceInfo(name="e-Stat (政府統計)", category="academic", is_overseas=False, method="api_free", cost="¥0"),
        # 書籍
        SourceInfo(name="Amazon.co.jp Kindle", category="books", is_overseas=False, method="scraping", cost="¥0"),
        SourceInfo(name="Amazon.com", category="books", is_overseas=True, method="scraping", cost="¥0"),
        SourceInfo(name="Google Books", category="books", is_overseas=False, method="api_free_1000/day", cost="¥0"),
        SourceInfo(name="Goodreads", category="books", is_overseas=True, method="scraping", cost="¥0"),
        SourceInfo(name="国立国会図書館", category="books", is_overseas=False, method="api_free", cost="¥0"),
        # ニュース
        SourceInfo(name="Google News RSS (ja)", category="news", is_overseas=False, method="rss_free", cost="¥0"),
        SourceInfo(name="Google News RSS (en)", category="news", is_overseas=True, method="rss_free", cost="¥0"),
        SourceInfo(name="Yahoo News RSS", category="news", is_overseas=False, method="rss_free", cost="¥0"),
        SourceInfo(name="NHK RSS", category="news", is_overseas=False, method="rss_free", cost="¥0"),
        SourceInfo(name="BBC RSS", category="news", is_overseas=True, method="rss_free", cost="¥0"),
        SourceInfo(name="Reuters RSS", category="news", is_overseas=True, method="rss_free", cost="¥0"),
        SourceInfo(name="TechCrunch RSS", category="news", is_overseas=True, method="rss_free", cost="¥0"),
        SourceInfo(name="Hacker News RSS", category="news", is_overseas=True, method="rss_free", cost="¥0"),
        # Q&A
        SourceInfo(name="Yahoo!知恵袋", category="qa", is_overseas=False, method="scraping", cost="¥0"),
        SourceInfo(name="Stack Exchange", category="qa", is_overseas=True, method="api_free_10k/day", cost="¥0"),
        SourceInfo(name="教えて!goo", category="qa", is_overseas=False, method="scraping", cost="¥0"),
        SourceInfo(name="Reddit QA", category="qa", is_overseas=True, method="api_free", cost="¥0"),
        SourceInfo(name="Quora", category="qa", is_overseas=True, method="scraping", cost="¥0"),
    ]
