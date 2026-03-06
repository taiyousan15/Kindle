"""
動画プラットフォームコレクター（無料枠）

- YouTube Data API v3（10,000 units/日 無料）
  - 検索: 100 units/回 → 100回/日
  - 字幕: YouTubeTranscriptApi 使用
- TikTok: スクレイピング（ヘッドライン・ハッシュタグ）
"""
from __future__ import annotations

import asyncio
import re
import urllib.parse

import httpx
import structlog
from bs4 import BeautifulSoup

log = structlog.get_logger()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

_YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class VideoCollector:
    """YouTube（APIキーあり/なし両対応）+ TikTok 収集"""

    def __init__(self, settings) -> None:
        self._yt_key: str = getattr(settings, "youtube_api_key", "")

    async def collect(self, keyword: str) -> list[dict]:
        """YouTube 動画情報を収集"""
        if self._yt_key:
            videos = await self._youtube_api(keyword)
        else:
            videos = await self._youtube_scrape(keyword)

        # 英語動画から字幕を取得（海外活用素材として）
        videos = await self._enrich_with_captions(keyword, videos)
        return videos

    # ------------------------------------------------------------------
    # YouTube Data API v3（APIキーあり）
    # ------------------------------------------------------------------

    async def _youtube_api(self, keyword: str) -> list[dict]:
        """YouTube Data API で動画を検索（100 units/回）"""
        search_url = f"{_YOUTUBE_API_BASE}/search"
        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "maxResults": 20,
            "order": "viewCount",
            "key": self._yt_key,
        }
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(search_url, params=params)
            r.raise_for_status()
            data = r.json()

        video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
        if not video_ids:
            return []

        # 統計情報を取得（1 unit/本）
        stats_url = f"{_YOUTUBE_API_BASE}/videos"
        stats_params = {
            "part": "statistics,snippet",
            "id": ",".join(video_ids),
            "key": self._yt_key,
        }
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(stats_url, params=stats_params)
            r.raise_for_status()
            stats_data = r.json()

        results: list[dict] = []
        for item in stats_data.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            is_english = snippet.get("defaultAudioLanguage", "").startswith("en")
            results.append({
                "video_id": item["id"],
                "title": snippet.get("title", ""),
                "description": snippet.get("description", "")[:500],
                "channel": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "language": snippet.get("defaultAudioLanguage", ""),
                "is_overseas": is_english,
                "url": f"https://www.youtube.com/watch?v={item['id']}",
            })

        log.info("youtube_api_done", keyword=keyword, count=len(results))
        return results

    # ------------------------------------------------------------------
    # YouTube スクレイピング（APIキーなし）
    # ------------------------------------------------------------------

    async def _youtube_scrape(self, keyword: str) -> list[dict]:
        """YouTube をスクレイピングで検索（APIキー不要）"""
        try:
            from playwright.async_api import async_playwright
            encoded = urllib.parse.quote(keyword)
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(
                    f"https://www.youtube.com/results?search_query={encoded}&sp=CAMSAhAB",
                    wait_until="networkidle",
                    timeout=30000,
                )
                await page.wait_for_timeout(2000)

                # ytInitialData を抽出
                content = await page.content()
                await browser.close()

            # JSON データを正規表現で抽出
            match = re.search(r"var ytInitialData = ({.*?});</script>", content, re.DOTALL)
            if not match:
                return []

            yt_data = match.group(1)
            # 動画情報を抽出（簡易パース）
            titles = re.findall(r'"title":\{"runs":\[{"text":"([^"]+)"', yt_data)
            video_ids = re.findall(r'"videoId":"([^"]+)"', yt_data)
            views = re.findall(r'"viewCountText":\{"simpleText":"([^"]+)"', yt_data)

            results: list[dict] = []
            for i, (title, vid_id) in enumerate(zip(titles[:15], video_ids[:15])):
                results.append({
                    "video_id": vid_id,
                    "title": title,
                    "description": "",
                    "view_count_text": views[i] if i < len(views) else "",
                    "is_overseas": False,
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                })
            log.info("youtube_scrape_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("youtube_scrape_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # 字幕取得（英語動画のみ → 海外活用素材）
    # ------------------------------------------------------------------

    async def _enrich_with_captions(
        self, keyword: str, videos: list[dict]
    ) -> list[dict]:
        """英語動画から字幕を取得して追加"""
        en_videos = [v for v in videos if v.get("is_overseas")][:5]

        async def _get_caption(video: dict) -> dict:
            try:
                loop = asyncio.get_event_loop()
                transcript = await loop.run_in_executor(
                    None, self._sync_get_transcript, video["video_id"]
                )
                return {**video, "caption_text": transcript}
            except Exception:
                return {**video, "caption_text": ""}

        enriched_en = await asyncio.gather(*[_get_caption(v) for v in en_videos])
        en_ids = {v["video_id"] for v in en_videos}
        jp_videos = [v for v in videos if v["video_id"] not in en_ids]
        return list(enriched_en) + jp_videos

    def _sync_get_transcript(self, video_id: str) -> str:
        """youtube-transcript-api で字幕取得（同期）"""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, languages=["en", "en-US"]
            )
            return " ".join([t["text"] for t in transcript])[:2000]
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # YouTube コメント収集（人気コメント → 読者インサイト）
    # ------------------------------------------------------------------

    async def get_comments(self, video_id: str) -> list[dict]:
        """動画のトップコメントを収集"""
        if not self._yt_key:
            return []
        url = f"{_YOUTUBE_API_BASE}/commentThreads"
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": 50,
            "order": "relevance",
            "key": self._yt_key,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.get(url, params=params)
                r.raise_for_status()
                data = r.json()

            comments: list[dict] = []
            for item in data.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "text": comment.get("textDisplay", ""),
                    "like_count": comment.get("likeCount", 0),
                    "author": comment.get("authorDisplayName", ""),
                })
            return sorted(comments, key=lambda x: x["like_count"], reverse=True)
        except Exception as e:
            log.warning("youtube_comments_failed", error=str(e))
            return []
