"""Entry point for the URL shortener FastAPI application.

Run with:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import Base, engine
from app.api.routes import v1_router
from app.api.webhook_routes import webhook_router
from app.core.cache_utilities import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and open Redis connection on startup; close Redis on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    yield
    await close_redis()


app = FastAPI(title="URL Shortener", lifespan=lifespan)

app.include_router(v1_router)
app.include_router(webhook_router)




#Testing Idempotency
#Start the server

"""
uvicorn app.main:app --reload
celery -A app.celery_app.celery_app worker --loglevel=info
Step 1 — generate a key and make the first request


KEY=$(uuidgen)

curl -X POST http://localhost:8000/v1/links \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $KEY" \
  -d '{"long_url": "https://example.com"}'
Note the short_code in the response — e.g. "short_code": "X9D7FF".

Step 2 — send the exact same request again with the same key


curl -X POST http://localhost:8000/v1/links \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $KEY" \
  -d '{"long_url": "https://example.com"}'
What proves it worked:

You get back the exact same short_code as the first call
Check your database — only one row exists for that URL, not two
The worker terminal shows no second webhook task was queued
Step 3 — confirm a different key creates a new record


curl -X POST http://localhost:8000/v1/links \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"long_url": "https://example.com"}'
This returns a different short_code — a new row was created.

"""

#Testing the Dead Letter Queue
#Start the worker

"""
celery -A app.celery_app.celery_app worker --loglevel=info
Step 1 — register a webhook pointing at a dead URL


curl -X POST http://localhost:8000/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "dead-hook",
    "url": "http://localhost:9999/nowhere",
    "events": ["url.created"]
  }'
Note the id returned — e.g. 1.

Step 2 — trigger the event


curl -X POST http://localhost:8000/v1/links \
  -H "Content-Type: application/json" \
  -d '{"long_url": "https://google.com"}'
Watch the worker terminal — you will see 5 retry attempts with increasing delays, then a DLQ: error log.

Step 3 — inspect the DLQ


curl http://localhost:8000/v1/webhooks/dlq
You should see one entry with "is_resolved": false and the failure_reason showing the connection error.

Step 4 — replay it (pretend the endpoint is fixed by registering a live one first, or just test that the re-queue happens)


curl -X POST http://localhost:8000/v1/webhooks/dlq/1/replay
Worker terminal shows a new delivery attempt. Then check the DLQ again:


curl http://localhost:8000/v1/webhooks/dlq?resolved=true
The entry now shows "is_resolved": true and a replayed_at timestamp.

Step 5 — confirm double-replay is blocked


curl -X POST http://localhost:8000/v1/webhooks/dlq/1/replay
Returns 409 Conflict: Entry has already been replayed.

"""


##What Actually Happens When You Call self.retry()
"""
`self.retry(exc=exc, countdown=countdown)`
Celery does its own internal counting. It looks at its own self.request.retries — not your attempt variable. Your attempt variable disappears the moment the function ends.
First execution:
    self.request.retries = 0       ← Celery's counter
    attempt = 0 + 1 = 1             ← your local variable for logs
    self.retry() called
    Celery internally bumps: retries → 1
    Function ends, attempt is gone

Second execution (Celery reschedules the task):
    self.request.retries = 1       ← Celery's counter (still owns it)
    attempt = 1 + 1 = 2             ← your local variable, fresh again
    self.retry() called
    Celery internally bumps: retries → 2

"""