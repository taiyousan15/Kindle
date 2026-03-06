"""
書籍・出版情報コレクター

- Amazon.co.jp: Playwright スクレイピング（Kindleランキング）
- Amazon.com: Playwright スクレイピング（海外ランキング）
- Google Books API: 無料枠（1000 requests/日）
- 楽天ブックス: スクレイピング
- Goodreads: スクレイピング（海外レビュー）
- 国立国会図書館: 完全無料API
"""
from __future__ import annotations

import asyncio
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
    "Accept-Language": "ja-JP,ja;q=0.9",
}


class BookCollector:
    """書籍・出版情報を全ソースから収集"""

    def __init__(self, settings) -> None:
        self._settings = settings

    async def collect_all(self, keyword: str) -> list[SearchResult]:
        results_list = await asyncio.gather(
            self._amazon_jp_kindle(keyword),
            self._amazon_com(keyword),
            self._google_books(keyword),
            self._goodreads(keyword),
            self._ndl(keyword),
            return_exceptions=True,
        )
        items: list[SearchResult] = []
        for batch in results_list:
            if isinstance(batch, list):
                items.extend(batch)
        log.info("books_done", keyword=keyword, count=len(items))
        return items

    # ------------------------------------------------------------------
    # Amazon.co.jp Kindle ランキング（スクレイプ）
    # ------------------------------------------------------------------

    async def _amazon_jp_kindle(self, keyword: str) -> list[SearchResult]:
        """Amazon.co.jp のKindle検索結果をスクレイプ"""
        encoded = urllib.parse.quote(keyword)
        url = (
            f"https://www.amazon.co.jp/s?k={encoded}"
            "&i=digital-text&rh=n%3A2250738051&s=relevanceblender"
        )
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(extra_http_headers=_HEADERS)
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
                content = await page.content()
                await browser.close()

            soup = BeautifulSoup(content, "lxml")
            results: list[SearchResult] = []
            for item in soup.select("[data-component-type='s-search-result']")[:15]:
                title_el = item.select_one("h2 a span, .a-text-normal")
                price_el = item.select_one(".a-price .a-offscreen")
                rating_el = item.select_one(".a-icon-alt")
                review_el = item.select_one(".a-size-base.s-underline-text")
                asin = item.get("data-asin", "")

                title = title_el.get_text(strip=True) if title_el else ""
                price = price_el.get_text(strip=True) if price_el else ""
                rating = rating_el.get_text(strip=True) if rating_el else ""
                reviews = review_el.get_text(strip=True) if review_el else ""

                if title:
                    results.append(SearchResult(
                        title=title,
                        url=f"https://www.amazon.co.jp/dp/{asin}" if asin else url,
                        snippet=f"価格:{price} / 評価:{rating} / レビュー:{reviews}",
                        source="amazon_jp_kindle",
                        is_overseas=False,
                        raw={"asin": asin, "price": price, "rating": rating, "reviews": reviews},
                    ))
            log.info("amazon_jp_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("amazon_jp_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # Amazon.com（英語・海外）
    # ------------------------------------------------------------------

    async def _amazon_com(self, keyword: str) -> list[SearchResult]:
        """Amazon.com の英語Kindle本をスクレイプ（海外活用OK）"""
        encoded = urllib.parse.quote(f"{keyword} self help")
        url = f"https://www.amazon.com/s?k={encoded}&i=digital-text"
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(extra_http_headers={
                    **_HEADERS, "Accept-Language": "en-US,en;q=0.9"
                })
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
                content = await page.content()
                await browser.close()

            soup = BeautifulSoup(content, "lxml")
            results: list[SearchResult] = []
            for item in soup.select("[data-component-type='s-search-result']")[:15]:
                title_el = item.select_one("h2 a span, .a-text-normal")
                price_el = item.select_one(".a-price .a-offscreen")
                rating_el = item.select_one(".a-icon-alt")
                asin = item.get("data-asin", "")
                title = title_el.get_text(strip=True) if title_el else ""
                price = price_el.get_text(strip=True) if price_el else ""
                rating = rating_el.get_text(strip=True) if rating_el else ""

                if title:
                    results.append(SearchResult(
                        title=title,
                        url=f"https://www.amazon.com/dp/{asin}" if asin else url,
                        snippet=f"Price:{price} / Rating:{rating}",
                        source="amazon_com",
                        is_overseas=True,
                        raw={"asin": asin, "price": price, "rating": rating},
                    ))
            log.info("amazon_com_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("amazon_com_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # Google Books API（1000 requests/日 無料）
    # ------------------------------------------------------------------

    async def _google_books(self, keyword: str) -> list[SearchResult]:
        """Google Books API で書籍情報を取得"""
        url = "https://www.googleapis.com/books/v1/volumes"
        params = {
            "q": keyword,
            "maxResults": 15,
            "langRestrict": "ja",
            "printType": "books",
            "orderBy": "relevance",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.get(url, params=params)
                r.raise_for_status()
                data = r.json()

            results: list[SearchResult] = []
            for item in data.get("items", []):
                vol = item.get("volumeInfo", {})
                results.append(SearchResult(
                    title=vol.get("title", ""),
                    url=vol.get("infoLink", ""),
                    snippet=(
                        f"著者: {', '.join(vol.get('authors', []))[:50]} / "
                        f"出版: {vol.get('publishedDate', '')} / "
                        f"評価: {vol.get('averageRating', 'N/A')}"
                    ),
                    source="google_books",
                    is_overseas=False,
                    raw=vol,
                ))
            log.info("google_books_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("google_books_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # Goodreads（海外レビュー・スクレイプ）
    # ------------------------------------------------------------------

    async def _goodreads(self, keyword: str) -> list[SearchResult]:
        """Goodreads で英語書籍レビューを収集"""
        encoded = urllib.parse.quote(keyword)
        url = f"https://www.goodreads.com/search?q={encoded}&search_type=books"
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                headers={**_HEADERS, "Accept-Language": "en-US,en;q=0.9"},
                follow_redirects=True,
            ) as c:
                r = await c.get(url)
                r.raise_for_status()

            soup = BeautifulSoup(r.text, "lxml")
            results: list[SearchResult] = []
            for row in soup.select(".bookTitle, .tableList tr")[:15]:
                title_el = row.select_one(".bookTitle span, a.bookTitle")
                author_el = row.select_one(".authorName span")
                rating_el = row.select_one(".minirating")
                title = title_el.get_text(strip=True) if title_el else ""
                author = author_el.get_text(strip=True) if author_el else ""
                rating = rating_el.get_text(strip=True) if rating_el else ""
                if title:
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=f"Author: {author} / {rating}",
                        source="goodreads",
                        is_overseas=True,
                    ))
            log.info("goodreads_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("goodreads_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # 国立国会図書館 API（完全無料）
    # ------------------------------------------------------------------

    async def _ndl(self, keyword: str) -> list[SearchResult]:
        """国立国会図書館 デジタルコレクション API"""
        url = "https://iss.ndl.go.jp/api/opensearch"
        params = {
            "title": keyword,
            "cnt": 10,
            "media": "書籍",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS) as c:
                r = await c.get(url, params=params)
                r.raise_for_status()

            # RSS/Atom 形式で返ってくるのでXMLパース
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.text)
            ns = {
                "dc": "http://purl.org/dc/elements/1.1/",
                "atom": "http://www.w3.org/2005/Atom",
            }
            results: list[SearchResult] = []
            for item in root.iter("item")[:10]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                desc = item.findtext("description", "")[:200]
                if title:
                    results.append(SearchResult(
                        title=title,
                        url=link,
                        snippet=desc,
                        source="ndl",
                        is_overseas=False,
                    ))
            log.info("ndl_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("ndl_failed", error=str(e))
            return []
