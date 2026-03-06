"""
検索エンジン系コレクター（完全無料）

- DuckDuckGo HTML検索
- Google Suggest API（キーワード展開）
- Bing Autosuggest API（キーワード展開）
- Yahoo Japan Suggest（キーワード展開）
"""
from __future__ import annotations

import json
import re
import urllib.parse

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
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
}


class SearchEngineCollector:
    """DuckDuckGo検索 + Google/Bing/Yahoo サジェストでキーワード展開"""

    # ------------------------------------------------------------------
    # キーワード展開
    # ------------------------------------------------------------------

    async def expand_keywords(self, keyword: str) -> list[str]:
        """Google + Bing + Yahoo サジェストを統合してキーワードを展開"""
        results = await asyncio.gather(
            self._google_suggest(keyword),
            self._bing_suggest(keyword),
            self._yahoo_suggest(keyword),
            return_exceptions=True,
        )
        seen: set[str] = {keyword}
        expanded: list[str] = [keyword]
        for batch in results:
            if isinstance(batch, list):
                for kw in batch:
                    if kw not in seen:
                        seen.add(kw)
                        expanded.append(kw)
        log.info("keywords_expanded", seed=keyword, count=len(expanded))
        return expanded

    async def _google_suggest(self, keyword: str) -> list[str]:
        url = "https://suggestqueries.google.com/complete/search"
        params = {"client": "firefox", "q": keyword, "hl": "ja"}
        async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            return data[1] if len(data) > 1 else []

    async def _bing_suggest(self, keyword: str) -> list[str]:
        url = "https://api.bing.com/osjson.aspx"
        params = {"query": keyword, "market": "ja-JP"}
        async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            return data[1] if len(data) > 1 else []

    async def _yahoo_suggest(self, keyword: str) -> list[str]:
        url = "https://assist.search.yahoo.co.jp/suggest/complete"
        params = {"q": keyword, "output": "json"}
        async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            if "Result" in data and "List" in data["Result"]:
                return [item.get("Key", "") for item in data["Result"]["List"]]
            return []

    # ------------------------------------------------------------------
    # DuckDuckGo 検索
    # ------------------------------------------------------------------

    async def search_all(self, keyword: str, max_results: int = 20) -> list[SearchResult]:
        """DuckDuckGo で日本語・英語両方を検索"""
        ja_results, en_results = await asyncio.gather(
            self._duckduckgo_search(keyword, lang="ja-JP"),
            self._duckduckgo_search(f"{keyword} in english", lang="en-US"),
            return_exceptions=True,
        )
        items: list[SearchResult] = []
        if isinstance(ja_results, list):
            items.extend(ja_results)
        if isinstance(en_results, list):
            items.extend(en_results)
        return items[:max_results]

    async def _duckduckgo_search(self, query: str, lang: str = "ja-JP") -> list[SearchResult]:
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query, "kl": "jp-jp" if "ja" in lang else "us-en"}
        is_overseas = "en" in lang

        async with httpx.AsyncClient(
            timeout=15.0,
            headers={**_HEADERS, "Accept-Language": lang},
            follow_redirects=True,
        ) as c:
            r = await c.post(url, data=data)
            r.raise_for_status()

        soup = BeautifulSoup(r.text, "lxml")
        results: list[SearchResult] = []

        for result in soup.select(".result")[:15]:
            title_el = result.select_one(".result__title")
            url_el = result.select_one(".result__url")
            snippet_el = result.select_one(".result__snippet")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = url_el.get_text(strip=True) if url_el else ""
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            results.append(SearchResult(
                title=title,
                url=href,
                snippet=snippet,
                source="duckduckgo",
                is_overseas=is_overseas,
            ))

        log.info("duckduckgo_done", query=query, count=len(results))
        return results

    async def search_reddit_keywords(self, keyword: str) -> list[str]:
        """DuckDuckGo で Reddit の関連キーワードを抽出"""
        items = await self._duckduckgo_search(f"site:reddit.com {keyword}", lang="en-US")
        return [item.title for item in items]


# asyncio を遅延インポート（トップレベルのcircular importを避ける）
import asyncio  # noqa: E402
