"""
トレンド・需要調査コレクター（完全無料）

- Google Trends（pytrends）
- HackerNews Algolia API（完全無料）
- Yahoo Japan リアルタイム検索
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
import structlog
from bs4 import BeautifulSoup

from .engine import SearchResult

log = structlog.get_logger()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


class TrendsCollector:
    """Google Trends + HackerNews + Yahoo トレンド収集"""

    async def collect(self, keyword: str) -> dict:
        """Google Trends データを収集"""
        google, yahoo = await asyncio.gather(
            self._google_trends(keyword),
            self._yahoo_realtime(keyword),
            return_exceptions=True,
        )
        return {
            "google_trends": google if isinstance(google, dict) else {},
            "yahoo_realtime": yahoo if isinstance(yahoo, list) else [],
            "collected_at": datetime.utcnow().isoformat(),
        }

    async def collect_hackernews(self, keyword: str) -> list[SearchResult]:
        """HackerNews Algolia API（完全無料・無制限）"""
        url = "https://hn.algolia.com/api/v1/search"
        params = {
            "query": keyword,
            "tags": "story",
            "hitsPerPage": 20,
        }
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        results: list[SearchResult] = []
        for hit in data.get("hits", []):
            results.append(SearchResult(
                title=hit.get("title", ""),
                url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                snippet=f"Points: {hit.get('points', 0)} / Comments: {hit.get('num_comments', 0)}",
                source="hackernews",
                is_overseas=True,
                raw=hit,
            ))

        log.info("hackernews_done", keyword=keyword, count=len(results))
        return results

    async def _google_trends(self, keyword: str) -> dict:
        """pytrends を使ってGoogle Trendsデータを取得"""
        try:
            # pytrends はブロッキングなのでスレッドプールで実行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_google_trends, keyword)
        except Exception as e:
            log.warning("google_trends_failed", error=str(e))
            return {}

    def _sync_google_trends(self, keyword: str) -> dict:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="ja-JP", tz=540, timeout=(10, 25))
        pytrends.build_payload(
            [keyword],
            timeframe="today 3-m",
            geo="JP",
        )
        interest = pytrends.interest_over_time()
        related_queries = pytrends.related_queries()
        related_topics = pytrends.related_topics()

        # 週次平均を計算
        if not interest.empty and keyword in interest.columns:
            values = interest[keyword].tolist()
            avg = sum(values) / len(values) if values else 0
            trend_direction = "up" if values[-1] > avg else "down" if values[-1] < avg else "flat"
        else:
            avg = 0
            trend_direction = "unknown"
            values = []

        # 関連クエリ
        top_queries = []
        rising_queries = []
        if related_queries.get(keyword):
            top_df = related_queries[keyword].get("top")
            rising_df = related_queries[keyword].get("rising")
            if top_df is not None and not top_df.empty:
                top_queries = top_df["query"].tolist()[:10]
            if rising_df is not None and not rising_df.empty:
                rising_queries = rising_df["query"].tolist()[:10]

        return {
            "average_interest": round(avg, 1),
            "trend_direction": trend_direction,
            "weekly_values": values[-12:],  # 直近12週
            "top_related_queries": top_queries,
            "rising_related_queries": rising_queries,
        }

    async def _yahoo_realtime(self, keyword: str) -> list[str]:
        """Yahoo Japan リアルタイム検索のトレンドワード"""
        url = "https://search.yahoo.co.jp/realtime/search"
        params = {"p": keyword, "ei": "UTF-8"}
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                headers=_HEADERS,
                follow_redirects=True,
            ) as c:
                r = await c.get(url, params=params)
                r.raise_for_status()

            soup = BeautifulSoup(r.text, "lxml")
            words = []
            for el in soup.select(".realtime-word, .Trend, .trend-word")[:20]:
                text = el.get_text(strip=True)
                if text:
                    words.append(text)
            return words
        except Exception as e:
            log.warning("yahoo_realtime_failed", error=str(e))
            return []

    async def collect_producthunt(self, keyword: str) -> list[SearchResult]:
        """ProductHunt 最新プロダクトトレンド"""
        url = "https://www.producthunt.com/search"
        params = {"q": keyword}
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                headers=_HEADERS,
                follow_redirects=True,
            ) as c:
                r = await c.get(url, params=params)
                r.raise_for_status()

            soup = BeautifulSoup(r.text, "lxml")
            results: list[SearchResult] = []
            for item in soup.select("[data-test='product-item']")[:10]:
                title_el = item.select_one("h3, h2, .product-name")
                desc_el = item.select_one("p, .description")
                title = title_el.get_text(strip=True) if title_el else ""
                desc = desc_el.get_text(strip=True) if desc_el else ""
                if title:
                    results.append(SearchResult(
                        title=title,
                        url=f"https://www.producthunt.com/search?q={keyword}",
                        snippet=desc,
                        source="producthunt",
                        is_overseas=True,
                    ))
            return results
        except Exception as e:
            log.warning("producthunt_failed", error=str(e))
            return []
