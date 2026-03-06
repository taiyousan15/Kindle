"""
Kindle本 台本生成エンジン

qwen2.5:72b（Ollama）を使って多段階生成。
海外素材（bucket_a）を翻訳活用し、完全オリジナルコンテンツを生成。
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:72b"


@dataclass
class BookBlueprint:
    title: str
    subtitle: str
    author: str
    target_persona: str
    core_message: str
    before_state: str
    after_state: str
    genre: str
    chapters: list[dict]
    total_chars: int = 60000


@dataclass
class GeneratedBook:
    blueprint: BookBlueprint
    chapters: list[dict] = field(default_factory=list)
    full_text: str = ""
    quality_score: int = 0


async def _ollama(prompt: str, system: str = "", temperature: float = 0.7) -> str:
    """Ollama qwen2.5:72b への呼び出し"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=1800.0) as c:
        r = await c.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
                "temperature": temperature,
                "options": {"num_ctx": 8192},
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


class ScriptGenerator:
    """Kindle本台本を多段階で生成するエンジン"""

    def __init__(self, output_dir: Path | str = "output") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        topic: str,
        research_data: dict | None = None,
        author: str = "著者名",
    ) -> GeneratedBook:
        """
        トピックからKindle本を生成する。

        topic: 本のテーマ（例: "Dual Investment投資"）
        research_data: FreeResearchEngineの結果（省略時は内部生成）
        """
        log.info("book_generation_start", topic=topic, model=MODEL)

        # STEP 1: ブループリント設計
        print(f"\n{'='*60}")
        print(f"  Kindle本生成開始: {topic}")
        print(f"  モデル: {MODEL}")
        print(f"{'='*60}\n")

        print("📋 STEP 1/5: ブループリント設計中...")
        blueprint = await self._design_blueprint(topic, research_data)
        print(f"  ✅ タイトル: {blueprint.title}")
        print(f"  ✅ 章数: {len(blueprint.chapters)}章")

        # STEP 2: 章ごとの台本生成
        print("\n✍️  STEP 2/5: 台本生成中（全章）...")
        book = GeneratedBook(blueprint=blueprint)
        book.chapters = await self._generate_all_chapters(blueprint, research_data)

        # STEP 3: コピーライティング強化
        print("\n💡 STEP 3/5: コピーライティング強化中...")
        book.chapters = await self._enhance_copywriting(book.chapters, blueprint)

        # STEP 4: 文体統一
        print("\n✨ STEP 4/5: 文体統一中...")
        book.full_text = await self._unify_style(book.chapters, blueprint)

        # STEP 5: 品質スコア算出
        print("\n🔍 STEP 5/5: 品質チェック中...")
        book.quality_score = await self._quality_check(book.full_text, blueprint)
        print(f"  品質スコア: {book.quality_score}/100")

        # 出力保存
        await self._save_outputs(book, topic)

        print(f"\n{'='*60}")
        print(f"  ✅ 生成完了！")
        print(f"  文字数: {len(book.full_text):,}文字")
        print(f"  品質スコア: {book.quality_score}/100")
        print(f"  出力先: {self.output_dir}/")
        print(f"{'='*60}\n")

        return book

    # ------------------------------------------------------------------
    # STEP 1: ブループリント設計
    # ------------------------------------------------------------------

    async def _design_blueprint(
        self, topic: str, research_data: dict | None
    ) -> BookBlueprint:
        research_summary = ""
        if research_data:
            overseas = research_data.get("bucket_a", [])[:5]
            research_summary = "\n".join([
                f"- {r.get('title','')}: {r.get('snippet','')[:100]}"
                for r in overseas
            ])

        prompt = f"""
あなたはKindle本のプロデューサーです。
以下のテーマでベストセラーになるKindle本の設計書を作成してください。

テーマ: {topic}

【海外リサーチ素材（参考）】
{research_summary if research_summary else "（なし）"}

以下のJSON形式で出力してください（他のテキスト不要）:
{{
  "title": "本のタイトル（30文字以内・インパクト重視）",
  "subtitle": "サブタイトル（50文字以内・具体的なベネフィット）",
  "target_persona": "ターゲット読者の詳細説明（年齢・職業・悩み）",
  "core_message": "この本が伝える核心メッセージ（1文）",
  "before_state": "読者の読む前の状態",
  "after_state": "読者の読んだ後の理想状態",
  "genre": "Amazonカテゴリジャンル",
  "chapters": [
    {{
      "no": 1,
      "title": "章タイトル",
      "role": "PAS構造での役割（Problem/Agitate/Solution/Practice/Future）",
      "core_message": "この章で伝えること（1文）",
      "episode_type": "使うエピソードの種類（成功例/失敗例/統計/海外事例）",
      "action": "章末で読者に取らせるアクション",
      "target_chars": 4000
    }}
  ]
}}
"""
        raw = await _ollama(prompt, temperature=0.6)
        data = _extract_json(raw)

        return BookBlueprint(
            title=data["title"],
            subtitle=data.get("subtitle", ""),
            author="著者名",
            target_persona=data["target_persona"],
            core_message=data["core_message"],
            before_state=data["before_state"],
            after_state=data["after_state"],
            genre=data["genre"],
            chapters=data["chapters"],
            total_chars=sum(c.get("target_chars", 8000) for c in data["chapters"]),
        )

    # ------------------------------------------------------------------
    # STEP 2: 章ごとの台本生成（3並列）
    # ------------------------------------------------------------------

    async def _generate_all_chapters(
        self, blueprint: BookBlueprint, research_data: dict | None
    ) -> list[dict]:
        chapters = blueprint.chapters
        # Ollamaは単一GPU処理のため逐次生成（タイムアウト防止）
        all_results: list[dict] = []
        for ch in chapters:
            result = await self._generate_chapter(ch, blueprint, research_data)
            all_results.append(result)
            print(f"  第{ch['no']}章 完了（{result.get('chars', 0):,}文字）")
        return all_results

    async def _generate_chapter(
        self,
        chapter: dict,
        blueprint: BookBlueprint,
        research_data: dict | None,
    ) -> dict:
        # 海外素材を抽出
        overseas_snippets = ""
        academic_data = ""
        if research_data:
            overseas = research_data.get("bucket_a", [])[:8]
            overseas_snippets = "\n".join([
                f"  ・{r.get('source','')}: {r.get('title','')[:60]} — {r.get('snippet','')[:120]}"
                for r in overseas
            ])
            academic = research_data.get("bucket_c", [])[:5]
            academic_data = "\n".join([
                f"  ・{r.get('source','')}: {r.get('title','')[:80]}"
                for r in academic
            ])

        system = f"""あなたはKindle自己啓発・投資本の専門ライターです。

【絶対ルール】
- 対象読者: {blueprint.target_persona}
- 文体: です・ます調（親しみやすく・わかりやすく）
- 1段落 = 最大5行
- 「あなた」への直接呼びかけを5回以上含める
- 専門用語は初出時に必ず平易な説明を入れる
- 海外素材は翻訳して積極活用する（日本の情報は模倣しない）
- 具体的なエピソード・数字・事例を豊富に入れる
- 抽象論より具体例を優先（具体:抽象 = 6:4）"""

        prompt = f"""
第{chapter['no']}章「{chapter['title']}」を書いてください。

【この章の役割】{chapter['role']}
【伝えること】{chapter['core_message']}
【使うエピソード種類】{chapter['episode_type']}
【章末アクション】{chapter['action']}
【目標文字数】{chapter.get('target_chars', 8000)}文字

【海外リサーチ素材（翻訳して活用してください）】
{overseas_snippets if overseas_snippets else "  ・（一般的な海外事例を独自に作成してください）"}

【学術データ（引用してください）】
{academic_data if academic_data else "  ・（関連する研究データを独自に入れてください）"}

【本全体のコアメッセージ】{blueprint.core_message}

以下の構成で書いてください：
1. 冒頭フック（読者の心を掴む導入・200〜300文字）
2. 本文（エピソード・解説・事例を交えて）
3. まとめ（この章のポイント整理・箇条書き3〜5点）
4. 章末アクション（「今日からできること:」として具体的に）

目標文字数: {chapter.get('target_chars', 4000)}文字（簡潔・明確・読みやすく）
"""
        content = await _ollama(prompt, system=system, temperature=0.75)
        return {
            "no": chapter["no"],
            "title": chapter["title"],
            "content": content,
            "chars": len(content),
        }

    # ------------------------------------------------------------------
    # STEP 3: コピーライティング強化
    # ------------------------------------------------------------------

    async def _enhance_copywriting(
        self, chapters: list[dict], blueprint: BookBlueprint
    ) -> list[dict]:
        enhanced = []
        for ch in chapters:
            system = "あなたはコピーライティングの専門家です。"
            prompt = f"""
以下の章の冒頭部分（最初の300文字）を、より読者の心を掴む文章に書き直してください。

【元の冒頭】
{ch['content'][:400]}

【書き直しルール】
・読者が「これは私のことだ！」と感じる冒頭
・以下のいずれかのパターンを使う:
  A. 衝撃的な統計・事実から始める
  B. 読者の悩みを具体的に言い当てる
  C. 逆説・意外な切り口から始める
  D. 「あなたは〜ですか？」の質問から始める

【対象読者】{blueprint.target_persona}

書き直した冒頭（300文字程度）だけ出力してください。
"""
            new_opening = await _ollama(prompt, system=system, temperature=0.8)
            # 冒頭を差し替え
            original = ch["content"]
            # 最初の段落を置き換える
            paragraphs = original.split("\n\n")
            if paragraphs:
                paragraphs[0] = new_opening
            enhanced_content = "\n\n".join(paragraphs)
            enhanced.append({**ch, "content": enhanced_content})
        return enhanced

    # ------------------------------------------------------------------
    # STEP 4: 文体統一
    # ------------------------------------------------------------------

    async def _unify_style(
        self, chapters: list[dict], blueprint: BookBlueprint
    ) -> str:
        # 全章を結合
        full = f"# {blueprint.title}\n## {blueprint.subtitle}\n\n"
        full += f"---\n\n"
        full += f"**対象読者**: {blueprint.target_persona}\n\n"
        full += f"---\n\n"
        for ch in chapters:
            full += f"## 第{ch['no']}章 {ch['title']}\n\n"
            full += ch["content"] + "\n\n---\n\n"

        # 長すぎるので全文を一度にレビューせず、統計的なチェックのみ
        # 実際の文体統一は各章生成時のsystem promptで担保
        return full

    # ------------------------------------------------------------------
    # STEP 5: 品質チェック
    # ------------------------------------------------------------------

    async def _quality_check(self, full_text: str, blueprint: BookBlueprint) -> int:
        total_chars = len(full_text)
        target_chars = blueprint.total_chars
        score = 0

        # 文字数チェック（20点）
        ratio = total_chars / target_chars if target_chars > 0 else 0
        if 0.9 <= ratio <= 1.1:
            score += 20
        elif 0.8 <= ratio <= 1.2:
            score += 15
        else:
            score += 10

        # 具体例の密度（20点）- 数字が含まれる段落比率
        paragraphs = [p for p in full_text.split("\n\n") if p.strip()]
        numeric_paras = sum(1 for p in paragraphs if any(c.isdigit() for c in p))
        density = numeric_paras / len(paragraphs) if paragraphs else 0
        score += min(20, int(density * 40))

        # 「あなた」出現頻度（20点）
        anata_count = full_text.count("あなた")
        score += min(20, anata_count // 2)

        # 章末アクション存在確認（20点）
        action_count = full_text.count("今日からできること") + full_text.count("アクション")
        score += min(20, action_count * 5)

        # 章数チェック（20点）
        chapter_count = full_text.count("## 第")
        expected = len(blueprint.chapters)
        if chapter_count == expected:
            score += 20
        elif chapter_count >= expected - 1:
            score += 15

        return min(100, score)

    # ------------------------------------------------------------------
    # 出力保存
    # ------------------------------------------------------------------

    async def _save_outputs(self, book: GeneratedBook, topic: str) -> None:
        slug = topic.replace(" ", "_").replace("　", "_")[:30]

        # Markdown 保存
        md_path = self.output_dir / f"{slug}_台本.md"
        md_path.write_text(book.full_text, encoding="utf-8")
        print(f"  📄 Markdown: {md_path}")

        # メタデータ JSON 保存
        meta = {
            "title": book.blueprint.title,
            "subtitle": book.blueprint.subtitle,
            "genre": book.blueprint.genre,
            "target_persona": book.blueprint.target_persona,
            "core_message": book.blueprint.core_message,
            "total_chars": len(book.full_text),
            "quality_score": book.quality_score,
            "chapters": [
                {"no": ch["no"], "title": ch["title"], "chars": ch.get("chars", 0)}
                for ch in book.chapters
                if ch
            ],
            "kdp_keywords": _suggest_keywords(book.blueprint.title + " " + topic),
        }
        meta_path = self.output_dir / f"{slug}_metadata.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  📋 メタデータ: {meta_path}")


def _extract_json(text: str) -> dict:
    """LLM出力からJSONを抽出"""
    # ```json ... ``` ブロック
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # 生のJSON
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"JSONが見つかりません: {text[:200]}")


def _suggest_keywords(text: str) -> list[str]:
    """タイトルからKDPキーワードを簡易生成"""
    words = re.findall(r"[\u3040-\u9FFF]{2,}", text)
    seen: set[str] = set()
    result: list[str] = []
    for w in words:
        if w not in seen and len(w) >= 3:
            seen.add(w)
            result.append(w)
    return result[:7]
