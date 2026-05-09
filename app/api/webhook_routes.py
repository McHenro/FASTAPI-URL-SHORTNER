from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.dead_letter_webhook import DeadLetterWebhook
from app.schemas.webhook_schema import DLQEntryResponse, WebhookCreate, WebhookResponse
from app.services import webhook_service

webhook_router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@webhook_router.post("", response_model=WebhookResponse, status_code=201)
async def register_webhook(body: WebhookCreate, db: AsyncSession = Depends(get_db)):
    """Register a new webhook endpoint.

    Tip: grab a free listener URL from https://webhook.site then paste it here.
    Your URL shortener will POST to that URL every time a subscribed event fires.
    """
    return await webhook_service.create_webhook(
        db,
        name=body.name,
        url=body.url,
        events=[e.value for e in body.events],
    )


@webhook_router.get("", response_model=List[WebhookResponse])
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    """List all registered webhooks."""
    return await webhook_service.get_all_webhooks(db)


@webhook_router.delete("/{webhook_id}", status_code=204)
async def remove_webhook(webhook_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a webhook registration."""
    deleted = await webhook_service.delete_webhook(db, webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")


@webhook_router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: int, db: AsyncSession = Depends(get_db)):
    """Send a synthetic test payload to verify your endpoint is reachable.

    Use this right after registering a webhook to confirm it works before
    waiting for a real event to fire.
    """
    wh = await webhook_service.get_webhook_by_id(db, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return await webhook_service.test_webhook(wh)


# ── Dead-letter queue ──────────────────────────────────────────────────────────

@webhook_router.get("/dlq", response_model=List[DLQEntryResponse])
async def list_dead_letter_webhooks(
    resolved: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List webhook deliveries that have exhausted all retries.

    By default returns unresolved entries. Pass ?resolved=true to see
    entries that have already been replayed successfully.
    """
    result = await db.execute(
        select(DeadLetterWebhook)
        .where(DeadLetterWebhook.is_resolved == resolved)
        .order_by(DeadLetterWebhook.failed_at.desc())
    )
    return result.scalars().all()


@webhook_router.post("/dlq/{entry_id}/replay", status_code=202)
async def replay_dead_letter_webhook(entry_id: int, db: AsyncSession = Depends(get_db)):
    """Re-queue a failed webhook delivery.

    Marks the DLQ entry as resolved and enqueues a fresh delivery attempt
    with the original payload. The task will retry up to 5 times if needed.
    """
    result = await db.execute(
        select(DeadLetterWebhook).where(DeadLetterWebhook.id == entry_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    if entry.is_resolved:
        raise HTTPException(status_code=409, detail="Entry has already been replayed")

    from app.tasks.webhook_tasks import deliver_webhook
    deliver_webhook.delay(entry.webhook_id, entry.payload)

    entry.is_resolved = True
    entry.replayed_at = datetime.utcnow()
    await db.commit()

    return {"queued": True, "entry_id": entry_id, "webhook_id": entry.webhook_id}


@webhook_router.delete("/dlq/{entry_id}", status_code=204)
async def delete_dead_letter_webhook(entry_id: int, db: AsyncSession = Depends(get_db)):
    """Permanently delete a DLQ entry."""
    result = await db.execute(
        select(DeadLetterWebhook).where(DeadLetterWebhook.id == entry_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    await db.delete(entry)
    await db.commit()
