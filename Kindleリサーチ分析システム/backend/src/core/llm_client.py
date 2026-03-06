"""
LLMクライアント - プロバイダー自動選択。

優先順位:
  テキスト: Ollama (無料・ローカル) → OpenRouter → Anthropic直接
  ビジョン: OpenRouter Gemini Flash ($0.000075/枚) → mock fallback

コスト比較（表紙分析1枚あたり）:
  Anthropic Haiku直接: $0.0003
  OpenRouter Gemini Flash: $0.000075 (4倍安)
  Ollama llava (ローカル): $0.00 (ただしllava 4GB必要)
"""
import base64
import json
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_REFERER = "https://github.com/kindle-research"


class LLMClient:
    """
    マルチプロバイダーLLMクライアント。

    使い方:
        client = LLMClient(settings)
        text = await client.complete("タイトルを分析して", system="...")
        text = await client.complete_vision("表紙を分析して", image_b64, "image/jpeg")
    """

    def __init__(self, settings: Any) -> None:
        self._settings = settings
        self._ollama_available: bool | None = None  # None=未確認

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(self, prompt: str, system: str = "") -> str:
        """テキスト補完。Ollama → OpenRouter → Anthropic の順で試みる。"""
        provider = self._settings.llm_provider

        if provider in ("auto", "ollama"):
            if await self._ollama_alive():
                try:
                    return await self._ollama_complete(prompt, system)
                except Exception as e:
                    log.warning("ollama_complete_failed", error=str(e))

        if provider in ("auto", "openrouter") and self._settings.openrouter_api_key:
            try:
                return await self._openrouter_complete(
                    prompt, system, self._settings.openrouter_text_model
                )
            except Exception as e:
                log.warning("openrouter_complete_failed", error=str(e))

        if provider in ("auto", "anthropic") and self._settings.anthropic_api_key:
            try:
                return await self._anthropic_complete(prompt, system)
            except Exception as e:
                log.warning("anthropic_complete_failed", error=str(e))

        raise RuntimeError("利用可能なLLMプロバイダーがありません (Ollama/OpenRouter/Anthropic)")

    async def complete_vision(
        self,
        prompt: str,
        image_b64: str,
        media_type: str = "image/jpeg",
    ) -> str:
        """
        ビジョン補完。優先順位:
          1. Ollama qwen3-vl:8b (無料・ローカル) ← 既インストール済みなら最優先
          2. OpenRouter Gemini Flash ($0.000075/枚)
          3. Anthropic Haiku直接 ($0.0003/枚)
        """
        provider = self._settings.llm_provider

        if provider in ("auto", "ollama"):
            if await self._ollama_alive():
                try:
                    return await self._ollama_vision(prompt, image_b64, media_type)
                except Exception as e:
                    log.warning("ollama_vision_failed", error=str(e))

        if provider in ("auto", "openrouter") and self._settings.openrouter_api_key:
            try:
                return await self._openrouter_vision(prompt, image_b64, media_type)
            except Exception as e:
                log.warning("openrouter_vision_failed", error=str(e))

        if provider in ("auto", "anthropic") and self._settings.anthropic_api_key:
            try:
                return await self._anthropic_vision(prompt, image_b64, media_type)
            except Exception as e:
                log.warning("anthropic_vision_failed", error=str(e))

        raise RuntimeError("ビジョン対応LLMが設定されていません (Ollama qwen3-vl / OpenRouter / Anthropic)")

    # ------------------------------------------------------------------
    # Ollama
    # ------------------------------------------------------------------

    async def _ollama_alive(self) -> bool:
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            async with httpx.AsyncClient(timeout=2.0) as c:
                r = await c.get(f"{self._settings.ollama_base_url}/api/tags")
                self._ollama_available = r.status_code == 200
        except Exception:
            self._ollama_available = False
        log.info("ollama_health", available=self._ollama_available)
        return self._ollama_available

    async def _ollama_complete(self, prompt: str, system: str) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.post(
                f"{self._settings.ollama_base_url}/v1/chat/completions",
                json={
                    "model": self._settings.ollama_text_model,
                    "messages": messages,
                    "stream": False,
                },
            )
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    async def _ollama_vision(self, prompt: str, image_b64: str, media_type: str) -> str:
        """Ollama vision model (qwen3-vl:8b) を使った画像分析。"""
        data_url = f"data:{media_type};base64,{image_b64}"
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": prompt},
            ],
        }]
        async with httpx.AsyncClient(timeout=120.0) as c:  # 画像処理は時間がかかる
            r = await c.post(
                f"{self._settings.ollama_base_url}/v1/chat/completions",
                json={
                    "model": self._settings.ollama_vision_model,
                    "messages": messages,
                    "stream": False,
                },
            )
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------
    # OpenRouter (OpenAI互換エンドポイント)
    # ------------------------------------------------------------------

    def _openrouter_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "HTTP-Referer": OPENROUTER_REFERER,
            "Content-Type": "application/json",
        }

    async def _openrouter_complete(
        self, prompt: str, system: str, model: str
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers=self._openrouter_headers(),
                json={"model": model, "messages": messages, "max_tokens": 1024},
            )
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    async def _openrouter_vision(
        self, prompt: str, image_b64: str, media_type: str
    ) -> str:
        data_url = f"data:{media_type};base64,{image_b64}"
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": prompt},
            ],
        }]

        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers=self._openrouter_headers(),
                json={
                    "model": self._settings.openrouter_vision_model,
                    "messages": messages,
                    "max_tokens": 512,
                },
            )
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------
    # Anthropic 直接 (最終フォールバック)
    # ------------------------------------------------------------------

    async def _anthropic_complete(self, prompt: str, system: str) -> str:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        msg = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    async def _anthropic_vision(
        self, prompt: str, image_b64: str, media_type: str
    ) -> str:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        msg = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return msg.content[0].text
