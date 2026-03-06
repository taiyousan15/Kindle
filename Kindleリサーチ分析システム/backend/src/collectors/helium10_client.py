"""
Helium10 Cerebro / Magnet API クライアント。
日本市場（amazon.co.jp）対応。

料金: $129/月 (Platinum)
API Doc: https://www.helium10.com/tools/magnet/
"""
from dataclasses import dataclass

import httpx
import structlog

log = structlog.get_logger()

HELIUM10_API_BASE = "https://api.helium10.com/v1"


@dataclass(frozen=True)
class Helium10KeywordResult:
    keyword: str
    search_volume: int           # 月間推定検索数
    competitor_rank: int | None  # 競合ランク
    cpr: int | None              # Competitor Performance Rating
    note: str = "推定値 / Helium10 Magnet JP"


class Helium10Client:
    """
    Helium10 Magnet APIで日本Kindle市場のキーワードデータを取得する。
    APIキー未設定時はモックデータを返す（開発環境対応）。
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._base = HELIUM10_API_BASE

    async def get_keyword_volume(
        self,
        keyword: str,
        marketplace: str = "JP",
    ) -> Helium10KeywordResult | None:
        """
        Magnet API でキーワードの月間検索ボリュームを取得する。
        APIキー未設定時はNoneを返す。
        """
        if not self._api_key:
            log.debug("helium10_api_key_missing", keyword=keyword)
            return None

        url = f"{self._base}/keywords/search"
        params = {
            "keyword": keyword,
            "marketplace": marketplace,
            "sort": "search_volume",
        }
        headers = {
            "X-API-KEY": self._api_key,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            log.warning(
                "helium10_http_error",
                keyword=keyword,
                status=e.response.status_code,
            )
            return None
        except httpx.RequestError as e:
            log.warning("helium10_request_error", keyword=keyword, error=str(e))
            return None

        results = data.get("results", [])
        if not results:
            return None

        top = results[0]
        return Helium10KeywordResult(
            keyword=keyword,
            search_volume=top.get("search_volume", 0),
            competitor_rank=top.get("competitor_rank"),
            cpr=top.get("cpr"),
        )

    async def get_related_keywords(
        self,
        seed: str,
        limit: int = 20,
        marketplace: str = "JP",
    ) -> list[Helium10KeywordResult]:
        """Magnet APIで関連キーワード一覧を取得する。"""
        if not self._api_key:
            return []

        url = f"{self._base}/keywords/magnet"
        params = {
            "keyword": seed,
            "marketplace": marketplace,
            "limit": limit,
        }
        headers = {
            "X-API-KEY": self._api_key,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            log.warning("helium10_related_error", seed=seed, error=str(e))
            return []

        return [
            Helium10KeywordResult(
                keyword=item.get("keyword", ""),
                search_volume=item.get("search_volume", 0),
                competitor_rank=item.get("competitor_rank"),
                cpr=item.get("cpr"),
            )
            for item in data.get("results", [])
            if item.get("keyword")
        ]
