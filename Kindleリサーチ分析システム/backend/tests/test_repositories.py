"""リポジトリ層の単体テスト（SQLite インメモリ使用）。"""
import pytest
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.models.keyword_analysis import KeywordAnalysis
from src.db.repositories.keyword_repository import KeywordRepository

TEST_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def session():
    engine = create_async_engine(
        TEST_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # keyword_analyses テーブルだけ作成
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS keyword_analyses (
                keyword TEXT PRIMARY KEY,
                sv_merchant_words INTEGER,
                sv_autocomplete_score REAL,
                sv_helium10 INTEGER,
                sv_estimated INTEGER NOT NULL DEFAULT 0,
                sv_confidence INTEGER NOT NULL DEFAULT 1,
                sv_note TEXT,
                competition TEXT,
                book_count INTEGER,
                avg_bsr INTEGER,
                trend TEXT,
                related_keywords TEXT,
                top_asins TEXT,
                last_analyzed_at TEXT,
                sv_updated_at TEXT
            )
        """))

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


@pytest.mark.asyncio
async def test_keyword_repo_find_by_id_returns_none(session):
    repo = KeywordRepository(session)
    result = await repo.find_by_id("存在しないキーワード")
    assert result is None


@pytest.mark.asyncio
async def test_keyword_repo_find_all_empty(session):
    repo = KeywordRepository(session)
    results = await repo.find_all()
    assert results == []
