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

    # Anthropic (Claude)
    anthropic_api_key: str = ""

    # Helium10 (Phase2)
    helium10_api_key: str = ""

    # App settings
    app_name: str = "Kindleリサーチ分析システム"
    app_version: str = "1.0.0"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    # Batch settings
    bsr_update_interval_hours: int = 1
    keyword_refresh_interval_hours: int = 24
    max_bsr_asins_per_batch: int = 100
    cover_analysis_batch_size: int = 10  # Claude Vision コスト制御

    # Cost controls
    monthly_claude_budget_usd: float = 10.0  # Haiku Vision上限


@lru_cache
def get_settings() -> Settings:
    return Settings()
