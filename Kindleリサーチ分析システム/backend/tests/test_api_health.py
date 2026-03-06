"""ヘルスチェックとメトリクスエンドポイントのテスト。"""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestHealth:
    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_response_schema(self):
        data = client.get("/health").json()
        assert data["status"] == "ok"
        assert "app" in data
        assert "version" in data

    def test_metrics_returns_200(self):
        r = client.get("/metrics")
        assert r.status_code == 200

    def test_metrics_content_type(self):
        r = client.get("/metrics")
        assert "text/plain" in r.headers["content-type"]

    def test_metrics_contains_kindle_metrics(self):
        # BSR分析を1回呼んでからメトリクスを確認
        client.get("/api/v1/prediction/bsr-to-sales?bsr=5000")
        r = client.get("/metrics")
        assert "kindle_http_requests_total" in r.text
