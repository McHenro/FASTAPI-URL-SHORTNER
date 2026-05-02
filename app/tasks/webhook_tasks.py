"""Celery task: deliver a webhook payload to a single endpoint.

Replaces the asyncio.create_task(_deliver(...)) approach in webhook_service.py.
Key improvements over the old approach:
  - Survives worker restarts (task is re-queued if the worker dies mid-flight)
  - Automatic retry with exponential back-off on network / timeout errors
  - Visible in Flower (task state, retries, timing)
"""

import logging
import httpx
from app.celery_app import celery_app
from app.models.webhook import Webhook
from app.tasks.db import get_sync_db

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.webhook_tasks.deliver_webhook",
    max_retries=3,
    # Only retry on network/timeout problems — HTTP 4xx/5xx are the remote's fault.
    autoretry_for=(httpx.TimeoutException, httpx.RequestError),
    retry_backoff=True,       # 1s → 2s → 4s between retries
    retry_backoff_max=120,    # cap at 2 minutes
    retry_jitter=True,        # spread retries so bursts don't slam the endpoint
)
def deliver_webhook(self, webhook_id: int, payload: dict) -> None:
    """POST `payload` to the webhook endpoint identified by `webhook_id`.

    Args:
        webhook_id: Primary key of the Webhook row in the database.
        payload:    The JSON body built by webhook_service._build_payload().
    """
    with get_sync_db() as db:
        wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()

    if not wh or not wh.is_active:
        logger.info("Webhook %s is missing or inactive — skipping", webhook_id)
        return

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": payload["event"],
        "User-Agent": "URLShortener-Webhook/1.0",
    }

    response = httpx.post(wh.url, json=payload, headers=headers, timeout=10.0)
    logger.info(
        "Webhook %s → %s  status=%s  attempt=%s",
        webhook_id, wh.url, response.status_code, self.request.retries + 1,
    )
