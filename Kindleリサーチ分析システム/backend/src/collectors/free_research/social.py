"""
SNS・コミュニティコレクター（完全無料）

- X (Twitter): Cookie認証（.envのTWITTER_AUTH_TOKEN使用）
- note: Playwright スクレイピング
- Reddit: 公開API（認証不要）
"""
from __future__ import annotations

import asyncio
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
}


class SocialCollector:
    """X + note + Reddit 統合収集"""

    def __init__(self, settings) -> None:
        self._settings = settings

    async def collect_all(self, keyword: str) -> list[SearchResult]:
        results_list = await asyncio.gather(
            self._collect_twitter(keyword),
            self._collect_note(keyword),
            self._collect_reddit(keyword),
            return_exceptions=True,
        )
        items: list[SearchResult] = []
        for batch in results_list:
            if isinstance(batch, list):
                items.extend(batch)
        return items

    # ------------------------------------------------------------------
    # X (Twitter) - Cookie認証
    # ------------------------------------------------------------------

    async def _collect_twitter(self, keyword: str) -> list[SearchResult]:
        """X の検索API（Cookie認証）でツイートを収集"""
        auth_token = getattr(self._settings, "twitter_auth_token", "")
        ct0 = getattr(self._settings, "twitter_ct0", "")
        if not auth_token or not ct0:
            log.warning("twitter_auth_missing")
            return []

        try:
            encoded = urllib.parse.quote(keyword)
            url = "https://api.twitter.com/2/tweets/search/recent"
            params = {
                "query": f"{keyword} lang:ja -is:retweet",
                "max_results": 20,
                "tweet.fields": "public_metrics,created_at,text",
            }
            headers = {
                **_HEADERS,
                "Cookie": f"auth_token={auth_token}; ct0={ct0}",
                "X-Csrf-Token": ct0,
                "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            }
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.get(url, params=params, headers=headers)
                if r.status_code != 200:
                    return await self._collect_twitter_scrape(keyword, auth_token, ct0)
                data = r.json()

            results: list[SearchResult] = []
            for tweet in data.get("data", []):
                metrics = tweet.get("public_metrics", {})
                results.append(SearchResult(
                    title=tweet["text"][:80],
                    url=f"https://twitter.com/i/web/status/{tweet['id']}",
                    snippet=f"いいね:{metrics.get('like_count',0)} RT:{metrics.get('retweet_count',0)}",
                    source="twitter",
                    is_overseas=False,
                    raw=tweet,
                ))
            log.info("twitter_api_done", keyword=keyword, count=len(results))
            return results

        except Exception as e:
            log.warning("twitter_failed", error=str(e))
            return []

    async def _collect_twitter_scrape(
        self, keyword: str, auth_token: str, ct0: str
    ) -> list[SearchResult]:
        """Twitter GraphQL API でスクレイピング"""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    extra_http_headers={"User-Agent": _HEADERS["User-Agent"]}
                )
                await ctx.add_cookies([
                    {"name": "auth_token", "value": auth_token, "domain": ".twitter.com", "path": "/"},
                    {"name": "ct0", "value": ct0, "domain": ".twitter.com", "path": "/"},
                ])
                page = await ctx.new_page()
                encoded = urllib.parse.quote(keyword)
                await page.goto(
                    f"https://twitter.com/search?q={encoded}&src=typed_query&f=live",
                    wait_until="networkidle",
                    timeout=30000,
                )
                await page.wait_for_timeout(3000)

                tweets = await page.query_selector_all("[data-testid='tweet']")
                results: list[SearchResult] = []
                for tweet in tweets[:15]:
                    text_el = await tweet.query_selector("[data-testid='tweetText']")
                    text = await text_el.inner_text() if text_el else ""
                    if text:
                        results.append(SearchResult(
                            title=text[:80],
                            url="https://twitter.com",
                            snippet=text,
                            source="twitter_scrape",
                            is_overseas=False,
                        ))
                await browser.close()
                log.info("twitter_scrape_done", keyword=keyword, count=len(results))
                return results
        except Exception as e:
            log.warning("twitter_scrape_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # note スクレイピング（Playwright）
    # ------------------------------------------------------------------

    async def _collect_note(self, keyword: str) -> list[SearchResult]:
        """note.com の検索結果を収集（日本語・参考のみ）"""
        try:
            # note は公開API経由でも取得可能
            url = "https://note.com/api/v2/searches"
            params = {
                "context": "note",
                "q": keyword,
                "size": 20,
                "start": 0,
                "sort": "like",
            }
            async with httpx.AsyncClient(
                timeout=15.0,
                headers=_HEADERS,
                follow_redirects=True,
            ) as c:
                r = await c.get(url, params=params)
                if r.status_code != 200:
                    return await self._collect_note_scrape(keyword)
                data = r.json()

            results: list[SearchResult] = []
            for item in data.get("data", {}).get("notes", {}).get("contents", []):
                results.append(SearchResult(
                    title=item.get("name", ""),
                    url=f"https://note.com{item.get('noteUrl', '')}",
                    snippet=f"いいね:{item.get('likeCount', 0)} / {item.get('user', {}).get('nickname', '')}",
                    source="note",
                    is_overseas=False,
                    raw=item,
                ))
            log.info("note_api_done", keyword=keyword, count=len(results))
            return results

        except Exception as e:
            log.warning("note_api_failed", error=str(e))
            return await self._collect_note_scrape(keyword)

    async def _collect_note_scrape(self, keyword: str) -> list[SearchResult]:
        """note をPlaywrightでスクレイピング"""
        try:
            from playwright.async_api import async_playwright
            encoded = urllib.parse.quote(keyword)
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(
                    f"https://note.com/search?q={encoded}&context=note&mode=search",
                    wait_until="networkidle",
                    timeout=30000,
                )
                await page.wait_for_timeout(2000)
                articles = await page.query_selector_all(".o-noteContentHeader, article")
                results: list[SearchResult] = []
                for article in articles[:15]:
                    title_el = await article.query_selector("h3, h2, .o-noteContentHeader__title")
                    title = await title_el.inner_text() if title_el else ""
                    if title:
                        results.append(SearchResult(
                            title=title,
                            url=f"https://note.com/search?q={encoded}",
                            snippet="note記事（参考のみ・直接使用NG）",
                            source="note_scrape",
                            is_overseas=False,
                        ))
                await browser.close()
                return results
        except Exception as e:
            log.warning("note_scrape_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # Reddit（公開API・認証不要）
    # ------------------------------------------------------------------

    async def _collect_reddit(self, keyword: str) -> list[SearchResult]:
        """Reddit の公開API（OAuth不要）でスレッドを収集"""
        subreddits = [
            "productivity", "selfimprovement", "getdisciplined",
            "DecidingToBeBetter", "Habits", "psychology",
        ]
        results: list[SearchResult] = []
        # 全体検索
        try:
            url = "https://www.reddit.com/search.json"
            params = {
                "q": keyword,
                "sort": "relevance",
                "limit": 20,
                "t": "year",
            }
            headers = {**_HEADERS, "Accept": "application/json"}
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as c:
                r = await c.get(url, params=params)
                r.raise_for_status()
                data = r.json()

            for post in data.get("data", {}).get("children", []):
                p = post.get("data", {})
                results.append(SearchResult(
                    title=p.get("title", ""),
                    url=f"https://reddit.com{p.get('permalink', '')}",
                    snippet=f"Score:{p.get('score',0)} | Comments:{p.get('num_comments',0)} | r/{p.get('subreddit','')}",
                    source="reddit",
                    is_overseas=True,
                    raw=p,
                ))
        except Exception as e:
            log.warning("reddit_search_failed", error=str(e))

        log.info("reddit_done", keyword=keyword, count=len(results))
        return results
