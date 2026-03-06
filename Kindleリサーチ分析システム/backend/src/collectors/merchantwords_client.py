from dataclasses import dataclass

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

log = structlog.get_logger()


@dataclass(frozen=True)
class MerchantWordsResult:
    keyword: str
    search_volume: int
    monthly_trend: list[int]  # 直近12ヶ月
    data_source: str = "MerchantWords"
    note: str = "推定値 / Amazon公式データではありません"


class MerchantWordsClient:
    """
    MerchantWords API クライアント（amazon.co.jp対応）。
    検索ボリュームの主力ソース（$29/月）。
    注: Amazon公式データではなく収集推定値。表示時は必ず「推定値」と明示。
    """

    BASE_URL = "https://api.merchantwords.com/v2"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_volume(
        self,
        keyword: str,
        marketplace: str = "JP",
    ) -> MerchantWordsResult | None:
        """
        キーワードの月間推定検索ボリュームを取得する。
        APIキー未設定の場合はNoneを返す（graceful degradation）。
        """
        if not self._api_key:
            log.debug("merchantwords_skipped", reason="api_key_not_set")
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/keywords",
                    params={
                        "keyword": keyword,
                        "marketplace": marketplace,
                        "key": self._api_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            return MerchantWordsResult(
                keyword=keyword,
                search_volume=data.get("search_volume", 0),
                monthly_trend=data.get("monthly_trend", [0] * 12),
            )

        except httpx.HTTPStatusError as e:
            log.error("merchantwords_http_error", keyword=keyword, status=e.response.status_code)
            return None
        except Exception as e:
            log.error("merchantwords_failed", keyword=keyword, error=str(e))
            return None

    async def get_bulk_volumes(
        self,
        keywords: list[str],
        marketplace: str = "JP",
    ) -> dict[str, MerchantWordsResult | None]:
        results = {}
        for kw in keywords:
            results[kw] = await self.get_volume(kw, marketplace)
        return results
