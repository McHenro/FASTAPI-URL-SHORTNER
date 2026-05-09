"""Celery task: deliver a webhook payload to a registered endpoint.

Retry strategy:
  - Network / timeout errors  → retry with exponential backoff + jitter (~1–2 → ~2–4 → ~4–8 → ~8–16 → ~16–32 s)
  - HTTP 5xx (server error)   → same retry strategy
  - HTTP 4xx (client error)   → permanent failure, do NOT retry (remote misconfigured)
  - After 5 failed retries    → write to dead_letter_webhooks table
"""

import logging
import random

import httpx

from app.celery_app import celery_app
from app.models.webhook import Webhook
from app.tasks.db import get_sync_db

logger = logging.getLogger(__name__)

_MAX_RETRIES = 5


def _save_to_dlq(
    webhook_id: int,
    webhook_url: str,
    payload: dict,
    failure_reason: str,
    attempt_count: int,
) -> None:
    """Write a permanently-failed delivery to the dead_letter_webhooks table."""
    from app.models.dead_letter_webhook import DeadLetterWebhook

    with get_sync_db() as db:
        db.add(DeadLetterWebhook(
            webhook_id=webhook_id,
            webhook_url=webhook_url,
            payload=payload,
            failure_reason=failure_reason,
            attempt_count=attempt_count,
        ))
        db.commit()

    logger.error(
        "DLQ: webhook_id=%d url=%s reason=%r attempts=%d",
        webhook_id, webhook_url, failure_reason, attempt_count,
    )


def _backoff(retries: int) -> float:
    base_wait = 2 ** retries              # 1, 2, 4, 8, 16 seconds
    jitter    = random.uniform(0, base_wait)
    return base_wait + jitter


@celery_app.task(
    bind=True,
    name="app.tasks.webhook_tasks.deliver_webhook",
    max_retries=_MAX_RETRIES,
)
def deliver_webhook(self, webhook_id: int, payload: dict) -> None:
    with get_sync_db() as db:
        wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()

    if not wh or not wh.is_active:
        logger.info("Webhook %d missing or inactive — skipping", webhook_id)
        return


    attempt = self.request.retries + 1

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": payload.get("event", ""),
        "User-Agent": "URLShortener-Webhook/1.0",
    }

    # ── Network / timeout ────────────────────────────────────────────────────
    try:
        response = httpx.post(wh.url, json=payload, headers=headers, timeout=10.0)
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.warning(
            "Webhook %d network error attempt %d/%d: %s",
            webhook_id, attempt, _MAX_RETRIES + 1, exc,
        )
        if self.request.retries >= _MAX_RETRIES:
            _save_to_dlq(webhook_id, wh.url, payload, str(exc), attempt)
            return
        self.retry(exc=exc, countdown=_backoff(self.request.retries))
        return  # never reached — self.retry() raises; keeps linters happy

    logger.info(
        "Webhook %d → %s  status=%d  attempt=%d/%d",
        webhook_id, wh.url, response.status_code, attempt, _MAX_RETRIES + 1,
    )

    # ── HTTP 4xx — permanent failure, no retry ───────────────────────────────
    if 400 <= response.status_code < 500:
        logger.error(
            "Webhook %d permanent failure: HTTP %d — saving to DLQ",
            webhook_id, response.status_code,
        )
        _save_to_dlq(
            webhook_id, wh.url, payload,
            f"HTTP {response.status_code} (client error, not retried)",
            attempt,
        )
        return

    # ── HTTP 5xx — retry, then DLQ ───────────────────────────────────────────
    if response.status_code >= 500:
        logger.warning(
            "Webhook %d server error attempt %d/%d: HTTP %d",
            webhook_id, attempt, _MAX_RETRIES + 1, response.status_code,
        )
        if self.request.retries >= _MAX_RETRIES:
            _save_to_dlq(
                webhook_id, wh.url, payload,
                f"HTTP {response.status_code} after {attempt} attempts",
                attempt,
            )
            return
        self.retry(
            exc=Exception(f"HTTP {response.status_code}"),
            countdown=_backoff(self.request.retries),
        )
