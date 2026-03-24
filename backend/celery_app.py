import os
from celery import Celery
from celery.schedules import crontab
from .config import settings

celery_app = Celery(
    "fastapi_tasks",
    broker=os.environ.get("CELERY_BROKER_URL", f"{settings.REDIS_URL}/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", f"{settings.REDIS_URL}/0"),
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    # Fail fast when Redis is unavailable — don't block HTTP requests for 30s
    broker_connection_timeout=2,
    broker_transport_options={
        "socket_connect_timeout": 2,
        "socket_timeout": 2,
    },
    task_annotations={"*": {"rate_limit": "300/m"}},
    beat_schedule={
        # Every Sunday at 02:00 IST re-crawl all clients with a known website
        "weekly-recrawl-all-clients": {
            "task": "backend.tasks.weekly_recrawl_all_clients",
            "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
        },
        # Every day at 00:05 IST disable chatbots for expired plans
        "daily-disable-expired-clients": {
            "task": "backend.tasks.disable_expired_clients",
            "schedule": crontab(hour=0, minute=5),
        },
    },
)

# 👇 autodiscover tasks from backend package
celery_app.autodiscover_tasks(["backend"])
