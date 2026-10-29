"""VIXOR — Celery application configuration.

Configured to use Redis as broker and result backend. Task modules are
imported here so Celery can discover and register them.
"""

from celery import Celery  # type: ignore[import-untyped]

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "vixor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks_scan",
        "app.workers.tasks_discovery",
        "app.workers.tasks_ml",
        "app.workers.tasks_schedule",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.SCAN_TOOL_TIMEOUT_SECONDS,
    worker_max_tasks_per_child=50,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "dispatch-due-schedules": {
            "task": "app.workers.tasks_schedule.dispatch_due_schedules",
            "schedule": 60.0,
        },
    },
)
