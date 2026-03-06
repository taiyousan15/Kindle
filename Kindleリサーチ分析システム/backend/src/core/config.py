from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://kindle_user:kindle_pass@localhost:5432/kindle_research"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Amazon Creators API (PA-API後継)
    amazon_access_key: str = ""
    amazon_secret_key: str = ""
    amazon_partner_tag: str = ""
    amazon_marketplace_id: str = "AN1VRQENFRJN5"  # amazon.co.jp

    # Keepa API
    keepa_api_key: str = ""

    # MerchantWords API
    merchantwords_api_key: str = ""

    # Anthropic (Claude) - 直接使用時のフォールバック
    anthropic_api_key: str = ""

    # OpenRouter (優先LLMプロバイダー - Anthropic APIの代替)
    # OPENROUTER_API_KEY を自動読み込み
    openrouter_api_key: str = ""
    # テキスト分析モデル (OpenRouter経由)
    openrouter_text_model: str = "anthropic/claude-haiku-4-5"
    # 表紙ビジョン分析モデル (OpenRouter経由 - Gemini Flash: $0.000075/枚)
    openrouter_vision_model: str = "google/gemini-flash-1.5"

    # Ollama (ローカルLLM - 完全無料)
    ollama_base_url: str = "http://localhost:11434"
    ollama_text_model: str = "qwen3:8b"         # テキスト分析 (既インストール済み)
    ollama_vision_model: str = "qwen3-vl:8b"    # 表紙画像分析 (既インストール済み・無料!)

    # LLMプロバイダー選択: "auto" / "ollama" / "openrouter" / "anthropic"
    # auto: Ollama生存確認 → OpenRouter → Anthropic直接 の順でフォールバック
    llm_provider: str = "auto"

    # Helium10 (Phase2)
    helium10_api_key: str = ""

    # YouTube Data API v3（無料枠: 10,000 units/日）
    youtube_api_key: str = ""

    # Twitter/X Cookie認証
    twitter_auth_token: str = ""
    twitter_ct0: str = ""
    twitter_twid: str = ""

    # App settings
    app_name: str = "Kindleリサーチ分析システム"
    app_version: str = "1.0.0"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    # Batch settings
    bsr_update_interval_hours: int = 1
    keyword_refresh_interval_hours: int = 24
    max_bsr_asins_per_batch: int = 100
    cover_analysis_batch_size: int = 10

    # Cost controls (OpenRouter換算)
    monthly_llm_budget_usd: float = 5.0  # Gemini Flash換算で約6万枚分


@lru_cache
def get_settings() -> Settings:
    return Settings()
