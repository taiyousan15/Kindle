from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Route

from src.api.routes import covers, genres, keywords, prediction, title
from src.api.routes import research
from src.core.config import get_settings
from src.core.metrics import metrics_endpoint
from src.core.middleware import PrometheusMiddleware
from src.db.database import engine
from src.db.models import (  # noqa: F401
    BookCover, BookReview, BSRHistory, CollectionJob,
    GenreTrend, KeywordAnalysis, KindleBook,
)

log = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", app=settings.app_name, version=settings.app_version)
    yield
    await engine.dispose()
    log.info("shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Amazon Kindle本リサーチ分析システム API",
    lifespan=lifespan,
)

app.add_middleware(PrometheusMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus scrape エンドポイント
app.add_route("/metrics", metrics_endpoint, include_in_schema=False)

# ルーター登録
app.include_router(keywords.router, prefix="/api/v1")
app.include_router(genres.router, prefix="/api/v1")
app.include_router(prediction.router, prefix="/api/v1")
app.include_router(title.router, prefix="/api/v1")
app.include_router(covers.router, prefix="/api/v1")
app.include_router(research.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }
