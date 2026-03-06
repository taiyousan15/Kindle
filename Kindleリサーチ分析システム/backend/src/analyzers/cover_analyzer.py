import base64
import json
from dataclasses import dataclass

import httpx
import structlog

log = structlog.get_logger()

COVER_ANALYSIS_PROMPT = """この書籍の表紙画像を分析してください。

以下をJSON形式で回答してください（日本語）:
{
  "primary_colors": ["#XXXXXX", "#XXXXXX"],
  "font_style": "serif または sans-serif または handwriting または display のいずれか",
  "layout": "text-dominant または image-dominant または balanced のいずれか",
  "mood": "professional または casual または dramatic または minimalist または academic のいずれか",
  "ctr_score": 0から100の整数（推定クリック率スコア）,
  "analysis": "表紙の特徴の簡潔な説明（100字以内）"
}

JSONのみを返してください。説明文は不要です。"""


@dataclass(frozen=True)
class CoverAnalysis:
    asin: str
    primary_colors: list[str]
    font_style: str
    layout: str
    mood: str
    ctr_score: int
    analysis_text: str
    raw_json: dict


class CoverAnalyzer:
    """
    Claude Haiku Vision API を使った表紙画像分析。
    モデル: claude-haiku-4-5 (コスト: $0.0003/枚)
    APIキー未設定の場合はモックデータを返す。
    """

    MODEL = "claude-haiku-4-5-20251001"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def analyze(self, image_url: str, asin: str) -> CoverAnalysis:
        """表紙画像URLを受け取り、Claude Vision で分析する。"""
        if not self._api_key:
            log.warning("cover_analyzer_no_api_key", asin=asin, using="mock")
            return self._mock_analysis(asin)

        if not image_url:
            log.warning("cover_analyzer_no_url", asin=asin)
            return self._mock_analysis(asin)

        try:
            # 画像をbase64エンコード
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.get(image_url)
                resp.raise_for_status()
                image_data = base64.standard_b64encode(resp.content).decode()
                media_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]

            client = self._get_client()
            message = await client.messages.create(
                model=self.MODEL,
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": COVER_ANALYSIS_PROMPT},
                    ],
                }],
            )

            raw_text = message.content[0].text
            result = json.loads(raw_text)

            return CoverAnalysis(
                asin=asin,
                primary_colors=result.get("primary_colors", []),
                font_style=result.get("font_style", "sans-serif"),
                layout=result.get("layout", "balanced"),
                mood=result.get("mood", "professional"),
                ctr_score=int(result.get("ctr_score", 50)),
                analysis_text=result.get("analysis", ""),
                raw_json=result,
            )

        except json.JSONDecodeError as e:
            log.error("cover_analyzer_json_parse_failed", asin=asin, error=str(e))
            return self._mock_analysis(asin)
        except Exception as e:
            log.error("cover_analyzer_failed", asin=asin, error=str(e))
            return self._mock_analysis(asin)

    def _mock_analysis(self, asin: str) -> CoverAnalysis:
        return CoverAnalysis(
            asin=asin,
            primary_colors=["#1A1A2E", "#FFFFFF"],
            font_style="sans-serif",
            layout="text-dominant",
            mood="professional",
            ctr_score=65,
            analysis_text="（モックデータ / Claude Vision API未設定）",
            raw_json={},
        )
