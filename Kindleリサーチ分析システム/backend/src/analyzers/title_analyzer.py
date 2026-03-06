import json
import re
from dataclasses import dataclass

import structlog

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
    Claude APIを使ったKindle本タイトル分析・改善提案。
    モデル: claude-haiku-4-5 (低コスト)
    APIキー未設定時はローカル分析にフォールバック。
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

        if not self._api_key:
            return self._local_analysis(title)

        try:
            client = self._get_client()
            message = await client.messages.create(
                model=self.MODEL,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": TITLE_ANALYSIS_PROMPT.format(
                        title=title,
                        genre=genre,
                        bestsellers=bestsellers_text,
                    ),
                }],
            )

            raw_text = message.content[0].text
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

        except Exception as e:
            log.error("title_analyzer_failed", title=title, error=str(e))
            return self._local_analysis(title)

    def _local_analysis(self, title: str) -> TitleAnalysisResult:
        """APIなしのローカル分析（フォールバック）。"""
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
            analysis="（ローカル分析 / Claude API未設定）",
        )
