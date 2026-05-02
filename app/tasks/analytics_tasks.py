"""Periodic Celery tasks for analytics and housekeeping.

Both tasks are registered in the beat_schedule inside celery_app.py:
  - daily_analytics_rollup  → midnight UTC every day
  - cleanup_expired_links   → every hour on the hour
"""

import logging
from app.celery_app import celery_app
from app.models.url import URL
from app.tasks.db import get_sync_db

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.analytics_tasks.daily_analytics_rollup")
def daily_analytics_rollup() -> None:
    """Log a daily summary of URLs stored in the system.

    This is intentionally simple for now — a future iteration can write
    aggregated click counts to a dedicated analytics table once a clicks
    column (or separate clicks model) is in place.
    """
    with get_sync_db() as db:
        total = db.query(URL).count()

    logger.info("Daily analytics rollup: %d total short URLs in system", total)


@celery_app.task(name="app.tasks.analytics_tasks.cleanup_expired_links")
def cleanup_expired_links() -> None:
    """Remove short URLs whose expiry date has passed.

    The URL model does not have an expires_at column yet, so this is a
    no-op placeholder. Add the column + the delete query here once the
    migration is in place.
    """
    logger.info("Cleanup: no expiry column defined yet — nothing to do")
