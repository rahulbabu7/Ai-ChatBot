import os
from celery import Celery
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
    task_annotations={"*": {"rate_limit": "300/m"}},
)

# 👇 autodiscover tasks from backend package
celery_app.autodiscover_tasks(["backend"])
