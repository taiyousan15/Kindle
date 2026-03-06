import json
import re
from dataclasses import dataclass

import structlog

from src.core.llm_client import LLMClient

log = structlog.get_logger()

TITLE_ANALYSIS_PROMPT = """以下の書籍タイトルを分析してください。

タイトル: {title}
ジャンル: {genre}
参考ベストセラー（同ジャンル上位）:
{bestsellers}

以下のJSONで回答してください:
{{
  "score": 0から100の整数（売れやすさスコア）,
  "length_chars": タイトルの文字数,
  "has_number": true/false（数字・数詞を含むか）,
  "has_benefit": true/false（読者へのベネフィットを示すか）,
  "has_target": true/false（ターゲット読者が明示されているか）,
  "structure": "how-to または question または statement または list のいずれか",
  "improvements": [
    "改善案1（具体的に）",
    "改善案2",
    "改善案3"
  ],
  "generated_titles": [
    "改善タイトル候補1",
    "改善タイトル候補2",
    "改善タイトル候補3"
  ],
  "analysis": "分析コメント（200字以内）"
}}

JSONのみを返してください。"""

SYSTEM_PROMPT = "あなたはAmazon Kindleの書籍マーケティング専門家です。日本語で回答してください。"


@dataclass(frozen=True)
class TitleAnalysisResult:
    original_title: str
    score: int  # 0〜100
    length_chars: int
    has_number: bool
    has_benefit: bool
    has_target: bool
    structure: str
    improvements: list[str]
    generated_titles: list[str]
    analysis: str


class TitleAnalyzer:
    """
    Kindle本タイトル分析・改善提案。

    プロバイダー優先順位 (config.llm_provider に従う):
      Ollama ローカル (llama3.2):   無料
      OpenRouter (Claude Haiku):    $0.000075/req
      Anthropic直接:                $0.0008/req
      未設定:                       ローカルルールベース分析にフォールバック
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def analyze(
        self,
        title: str,
        genre: str = "一般",
        bestseller_titles: list[str] | None = None,
    ) -> TitleAnalysisResult:
        """タイトルを分析し、改善案を生成する。"""
        bestsellers_text = "\n".join(
            f"- {t}" for t in (bestseller_titles or [])[:10]
        ) or "（データなし）"

        prompt = TITLE_ANALYSIS_PROMPT.format(
            title=title,
            genre=genre,
            bestsellers=bestsellers_text,
        )

        try:
            raw_text = await self._llm.complete(prompt, system=SYSTEM_PROMPT)
            raw_text = _extract_json(raw_text)
            result = json.loads(raw_text)

            return TitleAnalysisResult(
                original_title=title,
                score=int(result.get("score", 50)),
                length_chars=len(title),
                has_number=result.get("has_number", False),
                has_benefit=result.get("has_benefit", False),
                has_target=result.get("has_target", False),
                structure=result.get("structure", "statement"),
                improvements=result.get("improvements", []),
                generated_titles=result.get("generated_titles", []),
                analysis=result.get("analysis", ""),
            )

        except RuntimeError as e:
            # LLMプロバイダー未設定 → ローカルルールベース分析
            log.info("title_analyzer_fallback", title=title, reason=str(e))
            return self._local_analysis(title)
        except Exception as e:
            log.error("title_analyzer_failed", title=title, error=str(e))
            return self._local_analysis(title)

    def _local_analysis(self, title: str) -> TitleAnalysisResult:
        """APIなしのローカルルールベース分析（フォールバック）。"""
        has_number = bool(re.search(r'[0-9０-９一二三四五六七八九十百千万]', title))
        has_benefit = any(w in title for w in [
            "できる", "わかる", "マスター", "攻略", "完全", "最速", "稼ぐ",
            "入門", "初心者", "プロ", "上達", "成功",
        ])
        has_target = any(w in title for w in [
            "ための", "向け", "必読", "必携", "専門",
        ])
        chars = len(title)
        score = 50
        if 15 <= chars <= 30:
            score += 10
        if has_number:
            score += 10
        if has_benefit:
            score += 15
        if has_target:
            score += 10

        return TitleAnalysisResult(
            original_title=title,
            score=min(100, score),
            length_chars=chars,
            has_number=has_number,
            has_benefit=has_benefit,
            has_target=has_target,
            structure="statement",
            improvements=[
                "数字を含めてみましょう（例: 7つの方法）",
                "読者へのベネフィットを明示しましょう",
                "ターゲット読者を明示しましょう（例: 〜のための）",
            ],
            generated_titles=[
                f"【完全版】{title}",
                f"初心者でも{title}",
                f"プロが教える{title}",
            ],
            analysis="（ローカルルールベース分析 / LLM未設定）",
        )


def _extract_json(text: str) -> str:
    """```json ... ``` ブロックがあれば内側だけを返す。"""
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if m:
        return m.group(1)
    return text.strip()
