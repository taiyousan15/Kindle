"""
Prometheusメトリクス定義。
エンドポイント: GET /metrics
"""
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.requests import Request
from starlette.responses import Response

# HTTPリクエスト関連
http_requests_total = Counter(
    "kindle_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "kindle_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ビジネスメトリクス
bsr_analysis_total = Counter(
    "kindle_bsr_analysis_total",
    "Total BSR analysis calls",
    ["genre"],
)

keyword_search_total = Counter(
    "kindle_keyword_search_total",
    "Total keyword search calls",
)

cover_analysis_total = Counter(
    "kindle_cover_analysis_total",
    "Total cover analysis calls (Claude Vision)",
)

title_analysis_total = Counter(
    "kindle_title_analysis_total",
    "Total title analysis calls",
)

# 外部API
external_api_calls_total = Counter(
    "kindle_external_api_calls_total",
    "Total external API calls",
    ["api", "status"],
)

external_api_duration_seconds = Histogram(
    "kindle_external_api_duration_seconds",
    "External API call duration",
    ["api"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Celeryタスク
celery_tasks_total = Counter(
    "kindle_celery_tasks_total",
    "Total Celery task executions",
    ["task", "status"],
)

# DB接続プール
db_pool_size = Gauge(
    "kindle_db_pool_size",
    "Database connection pool size",
)

db_pool_checkedout = Gauge(
    "kindle_db_pool_checkedout",
    "Database connections currently checked out",
)


async def metrics_endpoint(_: Request) -> Response:
    """Prometheus scrape エンドポイント。"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
