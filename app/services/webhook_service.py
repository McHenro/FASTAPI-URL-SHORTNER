"""Webhook delivery and CRUD service.

How it works end-to-end:
  1. A caller registers a webhook via create_webhook() — stores the target URL +
     the list of events it cares about.
  2. When something interesting happens (URL created, clicked, deleted) the route
     handler calls fire_event().
  3. fire_event() loads all active webhooks whose `events` list includes the
     current event, builds a JSON payload, and schedules an async HTTP POST to
     each target URL using asyncio.create_task() — so the delivery is completely
     non-blocking; the API response returns immediately.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

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


async def _deliver(webhook: Webhook, payload: dict) -> None:
    """POST the payload to a single webhook URL. Errors are logged, never raised."""
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": payload["event"],
        "User-Agent": "URLShortener-Webhook/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook.url, json=payload, headers=headers)
            logger.info("Webhook %s → %s  status=%s", webhook.id, webhook.url, resp.status_code)
    except Exception as exc:
        logger.error("Webhook %s delivery failed to %s: %s", webhook.id, webhook.url, exc)


# ---------------------------------------------------------------------------
# Public: event firing
# ---------------------------------------------------------------------------

async def fire_event(db: AsyncSession, event: str, data: dict) -> None:
    """Fire `event` to every active webhook subscribed to it.

    Uses asyncio.create_task() so delivery is fire-and-forget — the HTTP call
    happens in the background and the API route returns without waiting.
    """
    result = await db.execute(select(Webhook).where(Webhook.is_active.is_(True)))
    webhooks: List[Webhook] = result.scalars().all()

    payload = _build_payload(event, data)

    for wh in webhooks:
        if event in (wh.events or []):
            # create_task schedules the coroutine on the running event loop
            # without blocking the current request
            asyncio.create_task(_deliver(wh, payload))


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
    """Send a synthetic test event to verify the endpoint is reachable."""
    payload = _build_payload(
        "webhook.test",
        {"message": "Test event from your URL Shortener — connection verified!"},
    )
    try:
        await _deliver(wh, payload)
        return {"success": True, "message": f"Test payload sent to {wh.url}"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}
