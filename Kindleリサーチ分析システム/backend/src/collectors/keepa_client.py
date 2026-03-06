from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

log = structlog.get_logger()

# Keepa Kindle Storeカテゴリコード (amazon.co.jp)
KINDLE_CATEGORY_CODE = "3045765051"

# Keepa時刻変換: Keepaは2011-01-01からの分数で時刻を表す
KEEPA_EPOCH = datetime(2011, 1, 1, tzinfo=timezone.utc)


def keepa_time_to_datetime(keepa_minutes: int) -> datetime:
    """Keepa時刻（分）をdatetimeに変換。"""
    from datetime import timedelta
    return KEEPA_EPOCH + timedelta(minutes=keepa_minutes)


@dataclass(frozen=True)
class BSRRecord:
    asin: str
    bsr: int
    category: str
    recorded_at: datetime
    data_source: str = "keepa"


@dataclass(frozen=True)
class BookKeepaData:
    asin: str
    title: str | None
    current_bsr: int | None
    bsr_history: list[BSRRecord]
    current_price: float | None
    review_count: int | None
    average_rating: float | None


class KeepaClient:
    """
    Keepa API クライアント（BSR履歴取得）。
    Kindle ASIN (B00xxx形式) のBSR履歴に正式対応確認済み。
    コスト: $54/月 (Basic: 20トークン/分)
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("KEEPA_API_KEY is required")
        self._api_key = api_key
        self._api = None

    def _get_api(self):
        if self._api is None:
            try:
                import keepa
                self._api = keepa.Keepa(self._api_key)
            except ImportError as e:
                raise RuntimeError("keepa package not installed: pip install keepa") from e
        return self._api

    def get_bsr_history(
        self,
        asins: list[str],
        days: int = 180,
    ) -> list[BookKeepaData]:
        """
        BSR履歴を一括取得する（最大100件/バッチ）。
        戻り値: BookKeepaDataのリスト
        """
        api = self._get_api()

        try:
            products = api.query(
                asins,
                domain="JP",
                history=True,
                days=days,
                stats=days,
            )
        except Exception as e:
            log.error("keepa_query_failed", asins_count=len(asins), error=str(e))
            return []

        results = []
        for product in products:
            asin = product.get("asin", "")
            title = product.get("title")
            current_price = self._extract_price(product)
            review_count = product.get("reviewCount")
            avg_rating = product.get("avg90", {}).get("RATING")
            if avg_rating:
                avg_rating = avg_rating / 10.0  # Keepaは10倍で格納

            bsr_records = self._extract_bsr_records(asin, product)
            current_bsr = bsr_records[-1].bsr if bsr_records else None

            results.append(
                BookKeepaData(
                    asin=asin,
                    title=title,
                    current_bsr=current_bsr,
                    bsr_history=bsr_records,
                    current_price=current_price,
                    review_count=review_count,
                    average_rating=avg_rating,
                )
            )

        log.info("keepa_query_complete", count=len(results))
        return results

    def _extract_bsr_records(
        self, asin: str, product: dict
    ) -> list[BSRRecord]:
        sales_ranks = product.get("salesRanks", {})
        kindle_data = sales_ranks.get(KINDLE_CATEGORY_CODE, [])

        records = []
        for i in range(0, len(kindle_data) - 1, 2):
            keepa_time = kindle_data[i]
            bsr_value = kindle_data[i + 1]
            if keepa_time > 0 and bsr_value > 0:
                records.append(
                    BSRRecord(
                        asin=asin,
                        bsr=bsr_value,
                        category="Kindleストア",
                        recorded_at=keepa_time_to_datetime(keepa_time),
                    )
                )

        return sorted(records, key=lambda r: r.recorded_at)

    def _extract_price(self, product: dict) -> float | None:
        csv = product.get("csv", {})
        kindle_price = csv.get("0", [])
        if len(kindle_price) >= 2:
            price_raw = kindle_price[-1]
            if price_raw and price_raw > 0:
                return price_raw / 100.0  # Keepaは円×100
        return None
