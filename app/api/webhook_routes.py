from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.webhook_schema import WebhookCreate, WebhookResponse
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
