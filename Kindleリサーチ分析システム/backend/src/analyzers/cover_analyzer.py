import base64
import json
from dataclasses import dataclass

import httpx
import structlog

from src.core.llm_client import LLMClient

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
    表紙画像分析。

    プロバイダー優先順位 (config.llm_provider に従う):
      OpenRouter Gemini Flash: $0.000075/枚 (推奨)
      Anthropic Haiku直接:     $0.0003/枚   (フォールバック)
      未設定:                  モックデータを返す
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def analyze(self, image_url: str, asin: str) -> CoverAnalysis:
        """表紙画像URLを受け取り、LLM Vision で分析する。"""
        if not image_url:
            log.warning("cover_analyzer_no_url", asin=asin)
            return self._mock_analysis(asin)

        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.get(image_url)
                resp.raise_for_status()
                image_b64 = base64.standard_b64encode(resp.content).decode()
                media_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]

            raw_text = await self._llm.complete_vision(
                COVER_ANALYSIS_PROMPT, image_b64, media_type
            )
            # JSONブロックを抽出（```json ... ``` の可能性あり）
            raw_text = _extract_json(raw_text)
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

        except RuntimeError as e:
            # LLMプロバイダー未設定
            log.warning("cover_analyzer_no_provider", asin=asin, error=str(e))
            return self._mock_analysis(asin)
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
            analysis_text="（モックデータ / LLM APIキー未設定）",
            raw_json={},
        )


def _extract_json(text: str) -> str:
    """```json ... ``` ブロックがあれば内側だけを返す。"""
    import re
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if m:
        return m.group(1)
    return text.strip()
