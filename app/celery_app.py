from celery import Celery
from celery.schedules import crontab
from app.core.config import settings


def create_celery_app() -> Celery:
    app = Celery(
        "url_shortener",
        broker=settings.celery_broker_url,
        backend=settings.celery_backend_url,
        include=[
            "app.tasks.webhook_tasks",
            "app.tasks.analytics_tasks",
        ],
    )

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        # Acknowledge only after the task finishes — if the worker dies mid-task
        # the message goes back to the queue rather than being lost.
        task_acks_late=True,
        worker_prefetch_multiplier=1,

        result_expires=86_400,    # Discard results after 24 h
        task_track_started=True,  # Surfaces STARTED state in Flower

        timezone="UTC",
        enable_utc=True,

        beat_schedule={
            "daily-analytics-rollup": {
                "task": "app.tasks.analytics_tasks.daily_analytics_rollup",
                "schedule": crontab(hour=0, minute=0),  # midnight UTC
            },
            "hourly-cleanup-expired-links": {
                "task": "app.tasks.analytics_tasks.cleanup_expired_links",
                "schedule": crontab(minute=0),           # every hour on the hour
            },
        },
    )

    return app


celery_app = create_celery_app()
