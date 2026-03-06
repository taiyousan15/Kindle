"""
Prometheusメトリクス収集ミドルウェア。
全HTTPリクエストのレイテンシ・ステータスを計測する。
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.metrics import http_request_duration_seconds, http_requests_total

# メトリクス収集をスキップするパス
_SKIP_PATHS = {"/metrics", "/health", "/favicon.ico"}


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in _SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        # パスをテンプレート化（動的セグメントを置換）
        route = self._normalize_path(path)

        http_requests_total.labels(
            method=request.method,
            endpoint=route,
            status=str(response.status_code),
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=route,
        ).observe(duration)

        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        """動的パスセグメントを{param}に置換してカーディナリティを抑える。"""
        parts = path.split("/")
        normalized = []
        for part in parts:
            if part and (
                # ASIN: B00xxxxxxx 形式
                (part.startswith("B") and len(part) == 10 and part[1:].isalnum())
                or part.isdigit()
            ):
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/".join(normalized)
