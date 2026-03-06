from celery import Celery
from celery.schedules import crontab

from src.core.config import get_settings

settings = get_settings()

app = Celery(
    "kindle_research",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.tasks.bsr_tasks",
        "src.tasks.keyword_tasks",
        "src.tasks.cover_tasks",
        "src.tasks.genre_tasks",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
    task_routes={
        "src.tasks.bsr_tasks.*": {"queue": "bsr"},
        "src.tasks.keyword_tasks.*": {"queue": "keywords"},
        "src.tasks.cover_tasks.*": {"queue": "covers"},
        "src.tasks.genre_tasks.*": {"queue": "default"},
    },
    beat_schedule={
        "bsr-update-hourly": {
            "task": "src.tasks.bsr_tasks.update_bsr_batch",
            "schedule": crontab(minute=0),
            "options": {"queue": "bsr"},
        },
        "keyword-refresh-daily": {
            "task": "src.tasks.keyword_tasks.refresh_keywords",
            "schedule": crontab(hour=3, minute=0),
            "options": {"queue": "keywords"},
        },
        "cover-analysis-daily": {
            "task": "src.tasks.cover_tasks.analyze_pending_covers",
            "schedule": crontab(hour=4, minute=0),
            "options": {"queue": "covers"},
        },
        "genre-trend-daily": {
            "task": "src.tasks.genre_tasks.compute_genre_trends",
            "schedule": crontab(hour=5, minute=0),
        },
    },
)
