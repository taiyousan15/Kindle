"""予測APIエンドポイントのテスト。"""
import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestBsrToSalesAPI:
    def test_returns_200(self):
        r = client.get("/api/v1/prediction/bsr-to-sales?bsr=1000")
        assert r.status_code == 200

    def test_response_schema(self):
        r = client.get("/api/v1/prediction/bsr-to-sales?bsr=5000&genre=ビジネス・経済")
        data = r.json()
        assert "bsr" in data
        assert "monthly_estimated" in data
        assert "lower_bound" in data
        assert "upper_bound" in data
        assert "error_range_pct" in data
        assert "note" in data
        assert data["error_range_pct"] == 20

    def test_note_contains_estimated(self):
        r = client.get("/api/v1/prediction/bsr-to-sales?bsr=5000")
        assert "推定値" in r.json()["note"]

    def test_invalid_bsr_returns_422(self):
        r = client.get("/api/v1/prediction/bsr-to-sales?bsr=0")
        assert r.status_code == 422

    def test_bsr_too_large_returns_422(self):
        r = client.get("/api/v1/prediction/bsr-to-sales?bsr=99999999")
        assert r.status_code == 422

    def test_missing_bsr_returns_422(self):
        r = client.get("/api/v1/prediction/bsr-to-sales")
        assert r.status_code == 422


class TestSimulateAPI:
    def test_returns_200(self):
        r = client.post(
            "/api/v1/prediction/simulate",
            json={"genre": "ビジネス・経済", "keyword": "投資", "target_bsr": 5000},
        )
        assert r.status_code == 200

    def test_response_schema(self):
        r = client.post(
            "/api/v1/prediction/simulate",
            json={"genre": "自己啓発", "keyword": "習慣", "target_bsr": 10000},
        )
        data = r.json()
        assert "feasibility" in data
        assert "recommendation" in data
        assert "monthly_sales" in data

    def test_high_difficulty_for_low_bsr(self):
        r = client.post(
            "/api/v1/prediction/simulate",
            json={"genre": "ビジネス・経済", "keyword": "投資", "target_bsr": 500},
        )
        assert r.json()["feasibility"] == "高難度"

    def test_easy_for_high_bsr(self):
        r = client.post(
            "/api/v1/prediction/simulate",
            json={"genre": "ビジネス・経済", "keyword": "投資", "target_bsr": 100_000},
        )
        assert r.json()["feasibility"] == "容易"

    def test_missing_fields_returns_422(self):
        r = client.post(
            "/api/v1/prediction/simulate",
            json={"genre": "ビジネス・経済"},
        )
        assert r.status_code == 422
