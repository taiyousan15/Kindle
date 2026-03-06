"""
FreeResearchEngine - 全無料ソースを並列収集するオーケストレーター

情報利用ポリシー:
  bucket_a (海外) -> 翻訳してそのまま活用OK
  bucket_b (日本) -> テーマ把握・インサイトのみ（直接使用NG）
  bucket_c (学術) -> 論文・統計データ（引用OK）
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    is_overseas: bool  # True=海外(直接活用OK) / False=日本(参考のみ)
    raw: dict = field(default_factory=dict)


@dataclass
class ResearchResult:
    keyword: str
    bucket_a: list[SearchResult] = field(default_factory=list)   # 海外・直接活用
    bucket_b: list[SearchResult] = field(default_factory=list)   # 日本・参考のみ
    bucket_c: list[dict] = field(default_factory=list)           # 学術・統計
    keywords_expanded: list[str] = field(default_factory=list)   # 展開キーワード
    trends: dict[str, Any] = field(default_factory=dict)         # トレンドデータ
    youtube_data: list[dict] = field(default_factory=list)       # YouTube情報
    news: list[dict] = field(default_factory=list)               # ニュース

    @property
    def total_sources(self) -> int:
        return len(self.bucket_a) + len(self.bucket_b) + len(self.bucket_c)


class FreeResearchEngine:
    """
    完全無料の89ソースリサーチエンジン。

    使い方:
        engine = FreeResearchEngine(settings)
        result = await engine.research("習慣化")
    """

    def __init__(self, settings: Any) -> None:
        self._settings = settings

    async def research(
        self,
        keyword: str,
        sources: list[str] | None = None,
    ) -> ResearchResult:
        """
        指定キーワードで全ソースを並列収集する。

        sources: 収集するソースグループ（省略時は全て）
          "search", "trends", "social", "video",
          "academic", "books", "news", "qa"
        """
        result = ResearchResult(keyword=keyword)
        active = set(sources) if sources else {
            "keywords", "search", "trends", "social",
            "video", "academic", "books", "news", "qa",
        }

        log.info("free_research_start", keyword=keyword, sources=list(active))

        # 並列実行
        tasks: list[asyncio.Task] = []

        if "keywords" in active:
            tasks.append(asyncio.create_task(
                self._run("keywords", self._collect_keywords(keyword, result))
            ))
        if "search" in active:
            tasks.append(asyncio.create_task(
                self._run("search", self._collect_search(keyword, result))
            ))
        if "trends" in active:
            tasks.append(asyncio.create_task(
                self._run("trends", self._collect_trends(keyword, result))
            ))
        if "social" in active:
            tasks.append(asyncio.create_task(
                self._run("social", self._collect_social(keyword, result))
            ))
        if "video" in active:
            tasks.append(asyncio.create_task(
                self._run("video", self._collect_video(keyword, result))
            ))
        if "academic" in active:
            tasks.append(asyncio.create_task(
                self._run("academic", self._collect_academic(keyword, result))
            ))
        if "books" in active:
            tasks.append(asyncio.create_task(
                self._run("books", self._collect_books(keyword, result))
            ))
        if "news" in active:
            tasks.append(asyncio.create_task(
                self._run("news", self._collect_news(keyword, result))
            ))
        if "qa" in active:
            tasks.append(asyncio.create_task(
                self._run("qa", self._collect_qa(keyword, result))
            ))

        await asyncio.gather(*tasks, return_exceptions=True)

        log.info(
            "free_research_done",
            keyword=keyword,
            total=result.total_sources,
            bucket_a=len(result.bucket_a),
            bucket_b=len(result.bucket_b),
            bucket_c=len(result.bucket_c),
        )
        return result

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    async def _run(self, name: str, coro) -> None:
        try:
            await coro
        except Exception as e:
            log.warning(f"collector_failed:{name}", error=str(e))

    async def _collect_keywords(self, keyword: str, result: ResearchResult) -> None:
        from .search_engines import SearchEngineCollector
        collector = SearchEngineCollector()
        expanded = await collector.expand_keywords(keyword)
        result.keywords_expanded = expanded

    async def _collect_search(self, keyword: str, result: ResearchResult) -> None:
        from .search_engines import SearchEngineCollector
        collector = SearchEngineCollector()
        items = await collector.search_all(keyword)
        for item in items:
            if item.is_overseas:
                result.bucket_a.append(item)
            else:
                result.bucket_b.append(item)

    async def _collect_trends(self, keyword: str, result: ResearchResult) -> None:
        from .trends import TrendsCollector
        collector = TrendsCollector()
        data = await collector.collect(keyword)
        result.trends.update(data)

        hn_items = await collector.collect_hackernews(keyword)
        result.bucket_a.extend(hn_items)

    async def _collect_social(self, keyword: str, result: ResearchResult) -> None:
        from .social import SocialCollector
        collector = SocialCollector(self._settings)
        items = await collector.collect_all(keyword)
        for item in items:
            if item.is_overseas:
                result.bucket_a.append(item)
            else:
                result.bucket_b.append(item)

    async def _collect_video(self, keyword: str, result: ResearchResult) -> None:
        from .video import VideoCollector
        collector = VideoCollector(self._settings)
        data = await collector.collect(keyword)
        result.youtube_data.extend(data)

    async def _collect_academic(self, keyword: str, result: ResearchResult) -> None:
        from .academic import AcademicCollector
        collector = AcademicCollector()
        items = await collector.collect_all(keyword)
        result.bucket_c.extend(items)

    async def _collect_books(self, keyword: str, result: ResearchResult) -> None:
        from .books import BookCollector
        collector = BookCollector(self._settings)
        items = await collector.collect_all(keyword)
        for item in items:
            if item.is_overseas:
                result.bucket_a.append(item)
            else:
                result.bucket_b.append(item)

    async def _collect_news(self, keyword: str, result: ResearchResult) -> None:
        from .news import NewsCollector
        collector = NewsCollector()
        items = await collector.collect_all(keyword)
        result.news.extend(items)

    async def _collect_qa(self, keyword: str, result: ResearchResult) -> None:
        from .qa import QACollector
        collector = QACollector()
        items = await collector.collect_all(keyword)
        for item in items:
            if item.is_overseas:
                result.bucket_a.append(item)
            else:
                result.bucket_b.append(item)
