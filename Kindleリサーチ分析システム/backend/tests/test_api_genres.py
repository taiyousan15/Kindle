"""ジャンルAPIエンドポイントのテスト。"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.main import app


async def _mock_db():
    """テスト用DBセッション（空結果を返す）。"""
    from unittest.mock import AsyncMock, MagicMock

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    execute_result.scalar_one_or_none.return_value = None

    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    yield session


app.dependency_overrides[get_db] = _mock_db
client = TestClient(app)


class TestGenresAPI:
    def test_list_genres_returns_200(self):
        r = client.get("/api/v1/genres")
        assert r.status_code == 200

    def test_list_genres_returns_list(self):
        r = client.get("/api/v1/genres")
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_genres_contains_business(self):
        r = client.get("/api/v1/genres")
        assert "ビジネス・経済" in r.json()

    def test_genre_trend_returns_200_or_empty(self):
        # DBなし環境では空リストを返す
        r = client.get("/api/v1/genres/ビジネス・経済/trend?period=monthly")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_genre_trend_invalid_period_returns_422(self):
        r = client.get("/api/v1/genres/ビジネス・経済/trend?period=invalid")
        assert r.status_code == 422

    def test_compare_genres_returns_dict(self):
        r = client.get("/api/v1/genres/compare?genres=ビジネス・経済,自己啓発")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)
