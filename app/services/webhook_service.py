"""Webhook delivery and CRUD service.

How it works end-to-end:
  1. A caller registers a webhook via create_webhook() — stores the target URL +
     the list of events it cares about.
  2. When something interesting happens (URL created, clicked, deleted) the route
     handler calls fire_event().
  3. fire_event() loads all active webhooks whose `events` list includes the
     current event, builds a JSON payload, and enqueues a Celery task for each
     matching webhook. The task delivers the HTTP POST in the background, with
     automatic retries on network failures.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook
from app.tasks.webhook_tasks import deliver_webhook

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_payload(event: str, data: dict) -> dict:
    return {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


# ---------------------------------------------------------------------------
# Public: event firing
# ---------------------------------------------------------------------------

async def fire_event(db: AsyncSession, event: str, data: dict) -> None:
    """Enqueue a Celery delivery task for every active webhook subscribed to `event`.

    The API response returns immediately — the HTTP POST to the webhook endpoint
    happens in the Celery worker process, not in the request lifecycle.
    """
    result = await db.execute(select(Webhook).where(Webhook.is_active.is_(True)))
    webhooks: List[Webhook] = result.scalars().all()

    payload = _build_payload(event, data)

    for wh in webhooks:
        if event in (wh.events or []):
            deliver_webhook.delay(wh.id, payload)


# ---------------------------------------------------------------------------
# Public: CRUD
# ---------------------------------------------------------------------------

async def create_webhook(
    db: AsyncSession,
    name: str,
    url: str,
    events: List[str],
) -> Webhook:
    wh = Webhook(name=name, url=url, events=events)
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


async def get_all_webhooks(db: AsyncSession) -> List[Webhook]:
    result = await db.execute(select(Webhook))
    return result.scalars().all()


async def get_webhook_by_id(db: AsyncSession, webhook_id: int) -> Optional[Webhook]:
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    return result.scalar_one_or_none()


async def delete_webhook(db: AsyncSession, webhook_id: int) -> bool:
    wh = await get_webhook_by_id(db, webhook_id)
    if not wh:
        return False
    await db.delete(wh)
    await db.commit()
    return True


async def test_webhook(wh: Webhook) -> dict:
    """Send a synchronous test event to verify the endpoint is reachable."""
    import httpx
    payload = _build_payload(
        "webhook.test",
        {"message": "Test event from your URL Shortener — connection verified!"},
    )
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": payload["event"],
        "User-Agent": "URLShortener-Webhook/1.0",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(wh.url, json=payload, headers=headers)
        return {"success": True, "message": f"Test payload sent to {wh.url} (status {resp.status_code})"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}
