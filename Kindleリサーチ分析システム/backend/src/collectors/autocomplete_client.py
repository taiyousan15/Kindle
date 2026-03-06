import asyncio
from dataclasses import dataclass

import httpx
import structlog

log = structlog.get_logger()

KINDLE_MARKETPLACE_ID = "AN1VRQENFRJN5"  # amazon.co.jp
AUTOCOMPLETE_URL = "https://completion.amazon.co.jp/api/2017/suggestions"


@dataclass(frozen=True)
class AutocompleteResult:
    keyword: str
    suggestions: list[str]
    autocomplete_score: float  # 0.0〜10.0
    note: str = "Autocompleteシグナル（需要の間接指標）"


class AutocompleteClient:
    """
    Amazon Autocomplete API クライアント（無料・合法）。
    Kindle Storeの実際の検索候補を取得し、需要シグナルとして使用。
    """

    def __init__(self, delay_seconds: float = 0.5) -> None:
        self._delay = delay_seconds

    async def get_suggestions(
        self,
        keyword: str,
        limit: int = 10,
    ) -> AutocompleteResult:
        await asyncio.sleep(self._delay)
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    AUTOCOMPLETE_URL,
                    params={
                        "alias": "digital-text",
                        "b2b": "0",
                        "fresh": "0",
                        "ks": "80",
                        "lop": "0",
                        "mid": KINDLE_MARKETPLACE_ID,
                        "plain": "1",
                        "prefix": keyword,
                        "event": "onKeyPress",
                        "limit": limit,
                        "fb": "1",
                        "suggestion-type[0]": "KEYWORD",
                    },
                    headers={"User-Agent": "Mozilla/5.0 (compatible; KindleResearch/1.0)"},
                )
                resp.raise_for_status()
                data = resp.json()

            suggestions = [s["value"] for s in data.get("suggestions", [])]
            score = min(10.0, len(suggestions) * 1.0)

            return AutocompleteResult(
                keyword=keyword,
                suggestions=suggestions,
                autocomplete_score=score,
            )

        except Exception as e:
            log.warning("autocomplete_failed", keyword=keyword, error=str(e))
            return AutocompleteResult(
                keyword=keyword,
                suggestions=[],
                autocomplete_score=0.0,
            )

    async def get_bulk_suggestions(
        self,
        keywords: list[str],
        limit: int = 10,
    ) -> dict[str, AutocompleteResult]:
        results = {}
        for kw in keywords:
            results[kw] = await self.get_suggestions(kw, limit)
        return results

    def calculate_volume_estimate(self, score: float) -> int:
        """
        Autocompleteスコアから推定月間検索数に変換。
        注: これは間接的な指標であり、信頼度は低い（★1相当）。
        """
        # score 1.0 → ~500, 5.0 → ~5000, 10.0 → ~20000
        if score <= 0:
            return 0
        elif score <= 3:
            return int(score * 500)
        elif score <= 7:
            return int(1500 + (score - 3) * 1500)
        else:
            return int(7500 + (score - 7) * 4167)
