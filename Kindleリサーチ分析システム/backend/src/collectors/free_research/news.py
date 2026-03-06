"""
ニュース・RSS フィードコレクター（完全無料）

全て RSS/Atom フィード経由 - feedparser 使用
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import feedparser
import httpx
import structlog

log = structlog.get_logger()

# RSS フィードURL一覧（全て無料・無制限）
RSS_FEEDS = {
    # 日本語（参考・インサイトのみ）
    "google_news_ja": "https://news.google.com/rss/search?q={keyword}&hl=ja&gl=JP&ceid=JP:ja",
    "yahoo_news_ja": "https://news.yahoo.co.jp/rss/topics/domestic.xml",
    "nhk": "https://www.nhk.or.jp/rss/news/cat0.xml",
    "hatena": "https://b.hatena.ne.jp/hotentry.rss",
    "techcrunch_jp": "https://jp.techcrunch.com/feed/",
    # 英語（海外・直接活用OK）
    "google_news_en": "https://news.google.com/rss/search?q={keyword}&hl=en&gl=US&ceid=US:en",
    "techcrunch": "https://techcrunch.com/feed/",
    "bbc": "http://feeds.bbci.co.uk/news/rss.xml",
    "reuters": "https://feeds.reuters.com/reuters/topNews",
    "theguardian": "https://www.theguardian.com/world/rss",
    "medium": "https://medium.com/feed/tag/{keyword}",
    "hacker_news": "https://hnrss.org/frontpage",
    "substack": "https://substack.com/feed",
}


class NewsCollector:
    """RSS フィードを全て無料で収集"""

    async def collect_all(self, keyword: str) -> list[dict]:
        """全 RSS ソースを並列収集"""
        tasks = [
            self._fetch_feed(name, url.format(keyword=keyword), keyword)
            for name, url in RSS_FEEDS.items()
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        items: list[dict] = []
        for batch in results_list:
            if isinstance(batch, list):
                items.extend(batch)

        # キーワード関連度でフィルタ
        keyword_lower = keyword.lower()
        filtered = [
            item for item in items
            if keyword_lower in item.get("title", "").lower()
            or keyword_lower in item.get("summary", "").lower()
            or not item.get("is_filtered")  # フィルタ不要のフィードはそのまま
        ]

        log.info("news_done", keyword=keyword, total=len(items), filtered=len(filtered))
        return filtered[:50]

    async def _fetch_feed(self, name: str, url: str, keyword: str) -> list[dict]:
        """RSS フィードを非同期で取得"""
        is_overseas = name in {
            "google_news_en", "techcrunch", "bbc", "reuters",
            "theguardian", "medium", "hacker_news", "substack",
        }
        try:
            # feedparser はブロッキングなのでスレッドプールで実行
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(
                None, self._sync_parse_feed, url
            )

            results: list[dict] = []
            for entry in feed.entries[:10]:
                published = ""
                if hasattr(entry, "published"):
                    published = entry.published
                elif hasattr(entry, "updated"):
                    published = entry.updated

                results.append({
                    "source": name,
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "summary": getattr(entry, "summary", "")[:300],
                    "published": published,
                    "is_overseas": is_overseas,
                    "is_filtered": True,  # キーワードフィルタ対象
                })
            log.debug("feed_done", name=name, count=len(results))
            return results
        except Exception as e:
            log.warning(f"feed_failed:{name}", error=str(e))
            return []

    def _sync_parse_feed(self, url: str) -> feedparser.FeedParserDict:
        return feedparser.parse(url, request_headers={
            "User-Agent": "KindleResearchBot/1.0"
        })

    async def collect_google_alerts(self, keyword: str) -> list[dict]:
        """Google News RSS でキーワードアラート"""
        ja_url = f"https://news.google.com/rss/search?q={keyword}&hl=ja&gl=JP&ceid=JP:ja"
        en_url = f"https://news.google.com/rss/search?q={keyword}&hl=en&gl=US&ceid=US:en"
        ja_items, en_items = await asyncio.gather(
            self._fetch_feed("google_news_ja", ja_url, keyword),
            self._fetch_feed("google_news_en", en_url, keyword),
            return_exceptions=True,
        )
        all_items: list[dict] = []
        if isinstance(ja_items, list):
            all_items.extend(ja_items)
        if isinstance(en_items, list):
            all_items.extend(en_items)
        return all_items

    async def collect_topic_feeds(self, genre: str) -> list[dict]:
        """ジャンル別のトピックRSSを収集"""
        genre_feeds = {
            "自己啓発": [
                "https://feeds.feedburner.com/LifeHacker",
                "https://www.psychologytoday.com/intl/rss.xml",
                "https://jamesclear.com/feed",
            ],
            "ビジネス": [
                "https://hbr.org/rss/feeds",
                "https://feeds.feedburner.com/fastcompany/headlines",
            ],
            "健康": [
                "http://feeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC",
                "https://www.healthline.com/rss/news",
            ],
            "マネー": [
                "https://feeds.feedburner.com/fool",
                "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
            ],
        }
        feeds = genre_feeds.get(genre, [])
        tasks = [
            self._fetch_feed(f"genre_{i}", url, genre)
            for i, url in enumerate(feeds)
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        items: list[dict] = []
        for batch in results_list:
            if isinstance(batch, list):
                items.extend(batch)
        return items
