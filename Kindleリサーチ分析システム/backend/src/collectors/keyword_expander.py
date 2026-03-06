"""
キーワード展開エンジン（完全無料）

単体キーワード → 関連・複合・英語展開まで自動生成。
Google Suggest + Bing + Yahoo + Ollama LLM で網羅。
"""
from __future__ import annotations

import asyncio

import httpx
import structlog

log = structlog.get_logger()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class KeywordExpander:
    """
    単体キーワードを多角的に展開する。

    使い方:
        expander = KeywordExpander(settings)
        result = await expander.expand("習慣化")
        # result.single / result.related / result.compound / result.english
    """

    def __init__(self, settings) -> None:
        self._settings = settings
        self._ollama_url = getattr(settings, "ollama_base_url", "http://localhost:11434")
        self._ollama_model = getattr(settings, "ollama_text_model", "qwen3:8b")

    async def expand(self, keyword: str) -> "KeywordTree":
        """キーワードを全方向に展開"""
        single, related, compound, english = await asyncio.gather(
            self._expand_single(keyword),
            self._expand_related(keyword),
            self._expand_compound(keyword),
            self._expand_english(keyword),
            return_exceptions=True,
        )

        def safe(val, default):
            return val if isinstance(val, list) else default

        tree = KeywordTree(
            seed=keyword,
            single=safe(single, [keyword]),
            related=safe(related, []),
            compound=safe(compound, []),
            english=safe(english, []),
        )
        log.info(
            "keyword_expanded",
            seed=keyword,
            total=len(tree.all_keywords),
        )
        return tree

    # ------------------------------------------------------------------
    # 単体キーワード（Google Suggest + Bing + Yahoo）
    # ------------------------------------------------------------------

    async def _expand_single(self, keyword: str) -> list[str]:
        """Google / Bing / Yahoo のサジェストを収集"""
        results = await asyncio.gather(
            self._google_suggest(keyword),
            self._bing_suggest(keyword),
            self._yahoo_suggest(keyword),
            return_exceptions=True,
        )
        seen: set[str] = {keyword}
        keywords: list[str] = [keyword]
        for batch in results:
            if isinstance(batch, list):
                for kw in batch:
                    kw = kw.strip()
                    if kw and kw not in seen:
                        seen.add(kw)
                        keywords.append(kw)
        return keywords[:20]

    async def _google_suggest(self, keyword: str) -> list[str]:
        url = "https://suggestqueries.google.com/complete/search"
        params = {"client": "firefox", "q": keyword, "hl": "ja"}
        async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            return data[1] if len(data) > 1 else []

    async def _bing_suggest(self, keyword: str) -> list[str]:
        url = "https://api.bing.com/osjson.aspx"
        params = {"query": keyword, "market": "ja-JP"}
        async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            return data[1] if len(data) > 1 else []

    async def _yahoo_suggest(self, keyword: str) -> list[str]:
        url = "https://assist.search.yahoo.co.jp/suggest/complete"
        params = {"q": keyword, "output": "json"}
        async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            if "Result" in data and "List" in data["Result"]:
                return [item.get("Key", "") for item in data["Result"]["List"]]
            return []

    # ------------------------------------------------------------------
    # 関連キーワード（Ollama LLMで生成）
    # ------------------------------------------------------------------

    async def _expand_related(self, keyword: str) -> list[str]:
        """Ollama で意味的に関連するキーワードを生成"""
        prompt = (
            f"「{keyword}」と意味的に関連する日本語キーワードを20個出してください。\n"
            f"・同義語、類義語、上位/下位概念を含む\n"
            f"・Kindle本のタイトルやジャンルに使われそうな言葉\n"
            f"・1行1キーワードで出力（番号不要）"
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(
                    f"{self._ollama_url}/v1/chat/completions",
                    json={
                        "model": self._ollama_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                )
                r.raise_for_status()
                text = r.json()["choices"][0]["message"]["content"]
            keywords = [
                line.strip().lstrip("・-・").strip()
                for line in text.strip().split("\n")
                if line.strip() and len(line.strip()) < 30
            ]
            return [k for k in keywords if k][:20]
        except Exception as e:
            log.warning("related_keywords_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # 複合キーワード（Ollama LLMで生成）
    # ------------------------------------------------------------------

    async def _expand_compound(self, keyword: str) -> list[str]:
        """Ollama で複合・掛け合わせキーワードを生成"""
        prompt = (
            f"「{keyword}」を使った複合キーワード（2〜4語）を20個生成してください。\n"
            f"・「{keyword} コツ」「{keyword} 方法」のような組み合わせ\n"
            f"・Kindle本で検索されそうな具体的なフレーズ\n"
            f"・読者の悩みを表すフレーズ（例: 「{keyword} 続かない 理由」）\n"
            f"・1行1キーワードで出力（番号不要）"
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(
                    f"{self._ollama_url}/v1/chat/completions",
                    json={
                        "model": self._ollama_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                )
                r.raise_for_status()
                text = r.json()["choices"][0]["message"]["content"]
            keywords = [
                line.strip().lstrip("・-").strip()
                for line in text.strip().split("\n")
                if line.strip() and len(line.strip()) < 50
            ]
            return [k for k in keywords if k][:20]
        except Exception as e:
            log.warning("compound_keywords_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # 英語展開（海外リサーチ用）
    # ------------------------------------------------------------------

    async def _expand_english(self, keyword: str) -> list[str]:
        """Ollama で英語キーワードに翻訳・展開"""
        prompt = (
            f"「{keyword}」を英語に翻訳し、海外でよく使われる関連英語キーワードを15個出してください。\n"
            f"・海外Kindle本やRedditで使われる自然な英語表現\n"
            f"・1行1キーワードで出力（番号不要）"
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(
                    f"{self._ollama_url}/v1/chat/completions",
                    json={
                        "model": self._ollama_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                )
                r.raise_for_status()
                text = r.json()["choices"][0]["message"]["content"]
            keywords = [
                line.strip().lstrip("・-").strip()
                for line in text.strip().split("\n")
                if line.strip() and all(ord(c) < 128 or c == " " for c in line.strip())
            ]
            return [k for k in keywords if k][:15]
        except Exception as e:
            log.warning("english_keywords_failed", error=str(e))
            return []


class KeywordTree:
    """展開されたキーワードツリー"""

    def __init__(
        self,
        seed: str,
        single: list[str],
        related: list[str],
        compound: list[str],
        english: list[str],
    ) -> None:
        self.seed = seed
        self.single = single
        self.related = related
        self.compound = compound
        self.english = english

    @property
    def all_keywords(self) -> list[str]:
        """全キーワードを重複除去して返す"""
        seen: set[str] = set()
        result: list[str] = []
        for kw in self.single + self.related + self.compound + self.english:
            if kw and kw not in seen:
                seen.add(kw)
                result.append(kw)
        return result

    def to_dict(self) -> dict:
        return {
            "seed": self.seed,
            "single": self.single,
            "related": self.related,
            "compound": self.compound,
            "english": self.english,
            "total": len(self.all_keywords),
        }
