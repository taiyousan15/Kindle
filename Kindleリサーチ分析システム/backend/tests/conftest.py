"""
pytest共通フィクスチャ。
DBはSQLite（インメモリ）を使用し、外部依存を排除する。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.database import Base, get_db
from src.main import app

# SQLite（asyncio対応）でテスト用DB
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        # pgvector / TimescaleDB 固有の型はSQLiteでスキップ
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def client():
    """FastAPI TestClient（DBなし、単体テスト用）。"""
    with TestClient(app) as c:
        yield c
