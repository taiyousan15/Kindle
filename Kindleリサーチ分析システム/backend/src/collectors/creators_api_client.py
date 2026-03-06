import asyncio
import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

log = structlog.get_logger()

PAAPI_HOST = "webservices.amazon.co.jp"
PAAPI_REGION = "us-west-2"
PAAPI_SERVICE = "ProductAdvertisingAPI"


@dataclass(frozen=True)
class BookMetadata:
    asin: str
    title: str
    author: list[str]
    genre: str | None
    bsr: int | None
    price: float | None
    kindle_unlimited: bool
    review_count: int | None
    average_rating: float | None
    cover_image_url: str | None  # APIから取得したURLのみ
    description: str | None
    published_date: datetime | None


class CreatorsApiClient:
    """
    Amazon Creators API クライアント (PA-API後継)。
    2026/4/30 PA-API廃止に伴い、Creators APIエンドポイントを使用。

    APIキー未設定の場合はモックデータを返す（開発・テスト用）。
    """

    BASE_URL = f"https://{PAAPI_HOST}/paapi5"
    RATE_LIMIT_DELAY = 1.1  # 1秒1リクエスト制限に準拠

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        partner_tag: str,
        marketplace_id: str = "AN1VRQENFRJN5",
    ) -> None:
        self._access_key = access_key
        self._secret_key = secret_key
        self._partner_tag = partner_tag
        self._marketplace_id = marketplace_id
        self._last_request_time = 0.0

    async def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.monotonic()

    def _sign(self, string_to_sign: str) -> str:
        return hmac.new(
            self._secret_key.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def search_books(
        self,
        keyword: str,
        category: str = "KindleStore",
        sort_by: str = "Relevance",
        page: int = 1,
    ) -> list[BookMetadata]:
        """キーワードでKindle本を検索する。"""
        if not self._access_key or not self._secret_key:
            log.warning("creators_api_not_configured", using="mock_data")
            return self._mock_search_results(keyword)

        await self._rate_limit()

        payload = {
            "Keywords": keyword,
            "Resources": [
                "Images.Primary.Large",
                "ItemInfo.Title",
                "ItemInfo.ByLineInfo",
                "ItemInfo.ContentInfo",
                "ItemInfo.ContentRating",
                "Offers.Listings.Price",
                "BrowseNodeInfo.BrowseNodes",
                "CustomerReviews.Count",
                "CustomerReviews.StarRating",
            ],
            "SearchIndex": category,
            "PartnerTag": self._partner_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.co.jp",
            "SortBy": sort_by,
            "ItemPage": page,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/searchitems",
                    json=payload,
                    headers=self._build_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

            return self._parse_search_results(data)

        except httpx.HTTPStatusError as e:
            log.error("creators_api_error", status=e.response.status_code, keyword=keyword)
            return []
        except Exception as e:
            log.error("creators_api_failed", keyword=keyword, error=str(e))
            return []

    def _build_headers(self) -> dict[str, str]:
        timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Amz-Date": timestamp,
            "Host": PAAPI_HOST,
        }

    def _parse_search_results(self, data: dict) -> list[BookMetadata]:
        items = data.get("SearchResult", {}).get("Items", [])
        results = []
        for item in items:
            results.append(self._parse_item(item))
        return results

    def _parse_item(self, item: dict) -> BookMetadata:
        asin = item.get("ASIN", "")
        info = item.get("ItemInfo", {})
        offers = item.get("Offers", {})
        reviews = item.get("CustomerReviews", {})
        images = item.get("Images", {})

        title_data = info.get("Title", {})
        title = title_data.get("DisplayValue", "")

        authors = []
        by_line = info.get("ByLineInfo", {})
        for contributor in by_line.get("Contributors", []):
            if contributor.get("RoleType") in ("author", "Author"):
                authors.append(contributor.get("DisplayValue", ""))

        price = None
        listings = offers.get("Listings", [])
        if listings:
            price_data = listings[0].get("Price", {})
            price = price_data.get("Amount")

        cover_url = None
        primary = images.get("Primary", {})
        large = primary.get("Large", {})
        cover_url = large.get("URL")

        return BookMetadata(
            asin=asin,
            title=title,
            author=authors or ["不明"],
            genre=None,
            bsr=None,
            price=price,
            kindle_unlimited=False,
            review_count=reviews.get("Count"),
            average_rating=reviews.get("StarRating", {}).get("Value"),
            cover_image_url=cover_url,
            description=None,
            published_date=None,
        )

    def _mock_search_results(self, keyword: str) -> list[BookMetadata]:
        """APIキー未設定時のモックデータ（開発・テスト用）。"""
        return [
            BookMetadata(
                asin=f"B0MOCK{i:04d}",
                title=f"【開発用モック】{keyword} 入門書 Vol.{i}",
                author=["テスト著者"],
                genre="コンピュータ・IT",
                bsr=i * 1000,
                price=550.0,
                kindle_unlimited=True,
                review_count=i * 10,
                average_rating=4.0,
                cover_image_url=None,
                description=f"{keyword}の入門書です。",
                published_date=None,
            )
            for i in range(1, 6)
        ]
