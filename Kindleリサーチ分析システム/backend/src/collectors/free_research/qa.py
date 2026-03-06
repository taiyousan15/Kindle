"""
Q&A・フォーラムコレクター（完全無料）

- Yahoo!知恵袋: スクレイピング（日本語悩み収集）
- Stack Exchange API: 完全無料・無制限
- Quora: スクレイピング（英語Q&A）
- 教えて!goo: スクレイピング
"""
from __future__ import annotations

import asyncio
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
    "Accept-Language": "ja-JP,ja;q=0.9",
}


class QACollector:
    """Q&Aサイトから読者の悩み・インサイトを収集"""

    async def collect_all(self, keyword: str) -> list[SearchResult]:
        results_list = await asyncio.gather(
            self._yahoo_chiebukuro(keyword),
            self._stack_exchange(keyword),
            self._oshiete_goo(keyword),
            self._reddit_qa(keyword),
            return_exceptions=True,
        )
        items: list[SearchResult] = []
        for batch in results_list:
            if isinstance(batch, list):
                items.extend(batch)
        log.info("qa_done", keyword=keyword, count=len(items))
        return items

    # ------------------------------------------------------------------
    # Yahoo! 知恵袋（日本語の悩み収集）
    # ------------------------------------------------------------------

    async def _yahoo_chiebukuro(self, keyword: str) -> list[SearchResult]:
        """Yahoo!知恵袋 で読者の生の悩みを収集"""
        encoded = urllib.parse.quote(keyword)
        url = f"https://chiebukuro.yahoo.co.jp/search?q={encoded}&flg=3"
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                headers=_HEADERS,
                follow_redirects=True,
            ) as c:
                r = await c.get(url)
                r.raise_for_status()

            soup = BeautifulSoup(r.text, "lxml")
            results: list[SearchResult] = []

            for item in soup.select(".SearchResult__item, .q-body, li.SearchResult")[:15]:
                title_el = item.select_one("h3 a, .SearchResult__titleLink, a[href*='chiebukuro']")
                snippet_el = item.select_one(".SearchResult__description, .q-detail-text, p")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                snippet = snippet_el.get_text(strip=True)[:200] if snippet_el else ""
                if title:
                    results.append(SearchResult(
                        title=title,
                        url=href if href.startswith("http") else f"https://chiebukuro.yahoo.co.jp{href}",
                        snippet=f"[読者の悩み] {snippet}",
                        source="yahoo_chiebukuro",
                        is_overseas=False,
                    ))
            log.info("chiebukuro_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("chiebukuro_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # Stack Exchange API（完全無料・10,000 req/日）
    # ------------------------------------------------------------------

    async def _stack_exchange(self, keyword: str) -> list[SearchResult]:
        """Stack Exchange で英語のQ&Aを収集"""
        sites = ["stackoverflow", "productivity", "lifehacks", "interpersonal"]
        tasks = [self._stack_exchange_site(keyword, site) for site in sites]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        items: list[SearchResult] = []
        for batch in results_list:
            if isinstance(batch, list):
                items.extend(batch)
        return items

    async def _stack_exchange_site(self, keyword: str, site: str) -> list[SearchResult]:
        url = "https://api.stackexchange.com/2.3/search/advanced"
        params = {
            "q": keyword,
            "site": site,
            "sort": "votes",
            "order": "desc",
            "pagesize": 10,
            "filter": "default",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(url, params=params)
                r.raise_for_status()
                data = r.json()

            results: list[SearchResult] = []
            for item in data.get("items", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=(
                        f"Score:{item.get('score', 0)} / "
                        f"Answers:{item.get('answer_count', 0)} / "
                        f"Views:{item.get('view_count', 0)}"
                    ),
                    source=f"stackexchange_{site}",
                    is_overseas=True,
                    raw=item,
                ))
            return results
        except Exception as e:
            log.warning(f"stackexchange_{site}_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # 教えて！goo（日本語Q&A）
    # ------------------------------------------------------------------

    async def _oshiete_goo(self, keyword: str) -> list[SearchResult]:
        """教えて!goo でQ&Aを収集"""
        encoded = urllib.parse.quote(keyword)
        url = f"https://oshiete.goo.ne.jp/search2/question/?MT={encoded}&status=BAK"
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                headers=_HEADERS,
                follow_redirects=True,
            ) as c:
                r = await c.get(url)
                r.raise_for_status()

            soup = BeautifulSoup(r.text, "lxml")
            results: list[SearchResult] = []
            for item in soup.select(".searchResult__item, .question-item")[:10]:
                title_el = item.select_one("a.searchResult__title, h3 a, .question-title a")
                snippet_el = item.select_one(".searchResult__text, .question-body")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                snippet = snippet_el.get_text(strip=True)[:200] if snippet_el else ""
                if title:
                    results.append(SearchResult(
                        title=title,
                        url=href if href.startswith("http") else f"https://oshiete.goo.ne.jp{href}",
                        snippet=f"[日本語Q&A] {snippet}",
                        source="oshiete_goo",
                        is_overseas=False,
                    ))
            log.info("oshiete_goo_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("oshiete_goo_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # Reddit サブレディット（英語コミュニティQ&A）
    # ------------------------------------------------------------------

    async def _reddit_qa(self, keyword: str) -> list[SearchResult]:
        """Reddit のQ&A/ディスカッションスレッドを収集"""
        # 自己啓発関連サブレディット
        subreddits = [
            "selfimprovement",
            "productivity",
            "getdisciplined",
            "Habits",
            "DecidingToBeBetter",
            "psychology",
            "LifeAdvice",
        ]
        results: list[SearchResult] = []
        for subreddit in subreddits[:3]:  # 負荷軽減で3つまで
            try:
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    "q": keyword,
                    "restrict_sr": True,
                    "sort": "top",
                    "t": "year",
                    "limit": 10,
                }
                async with httpx.AsyncClient(
                    timeout=10.0,
                    headers={**_HEADERS, "Accept": "application/json"},
                ) as c:
                    r = await c.get(url, params=params)
                    r.raise_for_status()
                    data = r.json()

                for post in data.get("data", {}).get("children", []):
                    p = post.get("data", {})
                    # Q&A形式のスレッドを優先
                    title = p.get("title", "")
                    if not title:
                        continue
                    results.append(SearchResult(
                        title=title,
                        url=f"https://reddit.com{p.get('permalink', '')}",
                        snippet=(
                            f"r/{subreddit} | "
                            f"Score:{p.get('score', 0)} | "
                            f"Comments:{p.get('num_comments', 0)} | "
                            f"{p.get('selftext', '')[:100]}"
                        ),
                        source=f"reddit_{subreddit}",
                        is_overseas=True,
                        raw=p,
                    ))
                await asyncio.sleep(0.5)  # Reddit のレート制限対策
            except Exception as e:
                log.warning(f"reddit_{subreddit}_failed", error=str(e))

        log.info("reddit_qa_done", keyword=keyword, count=len(results))
        return results

    # ------------------------------------------------------------------
    # Quora スクレイピング（英語Q&A）
    # ------------------------------------------------------------------

    async def _quora(self, keyword: str) -> list[SearchResult]:
        """Quora で英語のQ&Aを収集（ベストエフォート）"""
        encoded = urllib.parse.quote(keyword)
        url = f"https://www.quora.com/search?q={encoded}&type=question"
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(extra_http_headers={
                    **_HEADERS,
                    "Accept-Language": "en-US,en;q=0.9",
                })
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                items = await page.query_selector_all("[class*='question']")
                results: list[SearchResult] = []
                for item in items[:10]:
                    title_el = await item.query_selector("span[class*='title'], a span")
                    if title_el:
                        title = await title_el.inner_text()
                        if title and len(title) > 10:
                            results.append(SearchResult(
                                title=title,
                                url=url,
                                snippet="[Quora Q&A]",
                                source="quora",
                                is_overseas=True,
                            ))
                await browser.close()
                return results
        except Exception as e:
            log.warning("quora_failed", error=str(e))
            return []
