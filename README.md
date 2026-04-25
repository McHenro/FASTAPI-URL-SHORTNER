# URL Shortener

A production-style URL shortener built with **FastAPI**, **PostgreSQL** (via asyncpg + SQLAlchemy async ORM), and **Redis** as a write-through cache. Migrations are managed with **Alembic**. Outbound webhooks deliver real-time event notifications when URLs are created, clicked, or deleted.

---

## Project Structure

```
app/
├── api/
│   ├── routes.py          # All v1 URL endpoints
│   └── webhook_routes.py  # Webhook registration + management endpoints
├── core/
│   ├── config.py          # Pydantic settings — reads from .env
│   ├── database.py        # Async SQLAlchemy engine + session factory
│   └── cache_utilities.py # Async Redis helpers + url_cache_key
├── models/
│   ├── url.py             # URL ORM model
│   └── webhook.py         # Webhook ORM model
├── schemas/
│   ├── url_schema.py      # Pydantic request/response schemas for URLs
│   └── webhook_schema.py  # Pydantic schemas + WebhookEvent enum
├── services/
│   ├── url_service.py     # Business logic (create, resolve, delete)
│   └── webhook_service.py # Webhook CRUD + fire_event (fire-and-forget delivery)
└── main.py                # FastAPI app + lifespan (DB init, Redis init)
alembic/
├── env.py                 # Async-aware migration environment
├── script.py.mako         # Migration file template
└── versions/              # Auto-generated migration files live here
alembic.ini                # Alembic configuration
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/url_shortener
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=          # leave blank if no password
```

> `DATABASE_URL` **must** use the `postgresql+asyncpg://` scheme — the app uses an async engine.

---

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database (psql example)
createdb url_shortener

# 4. Run migrations (see Alembic section below)
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --reload
```

---

## API Endpoints

### URL Endpoints

All URL routes are prefixed with `/v1`.

| Method   | Path                    | Description                              |
|----------|-------------------------|------------------------------------------|
| `POST`   | `/v1/links`             | Create a new short URL                   |
| `GET`    | `/v1/links`             | List all stored short URLs               |
| `GET`    | `/v1/links/{short_code}`| Redirect (307) to the original long URL  |
| `DELETE` | `/v1/links/{short_code}`| Delete a short URL (also evicts cache)   |

#### POST /v1/links

**Request body:**
```json
{
  "long_url": "https://example.com/some/very/long/path",
  "title": "My Link"
}
```
`title` is optional.

**Response `201`:**
```json
{
  "short_code": "X9D7FF",
  "long_url": "https://example.com/some/very/long/path",
  "title": "My Link"
}
```

#### DELETE /v1/links/{short_code}

Returns `204 No Content` on success, `404` if the short code does not exist.

---

### Webhook Endpoints

All webhook routes are prefixed with `/v1/webhooks`.

| Method   | Path                          | Description                                    |
|----------|-------------------------------|------------------------------------------------|
| `POST`   | `/v1/webhooks`                | Register a new webhook endpoint                |
| `GET`    | `/v1/webhooks`                | List all registered webhooks                   |
| `DELETE` | `/v1/webhooks/{webhook_id}`   | Remove a webhook registration                  |
| `POST`   | `/v1/webhooks/{webhook_id}/test` | Send a synthetic test payload to the endpoint |

#### POST /v1/webhooks

**Request body:**
```json
{
  "name": "My Listener",
  "url": "https://webhook.site/your-unique-id",
  "events": ["url.created", "url.clicked", "url.deleted"]
}
```

**Response `201`:**
```json
{
  "id": 1,
  "name": "My Listener",
  "url": "https://webhook.site/your-unique-id",
  "events": ["url.created", "url.clicked", "url.deleted"],
  "is_active": true,
  "created_at": "2026-04-25T10:00:00+00:00"
}
```

**Supported events:**

| Event          | When it fires                              |
|----------------|--------------------------------------------|
| `url.created`  | A new short URL is successfully created    |
| `url.clicked`  | A redirect request resolves a short code   |
| `url.deleted`  | A short URL is deleted                     |

#### Webhook payload format

Every event delivers a JSON body in this shape:

```json
{
  "event": "url.created",
  "timestamp": "2026-04-25T10:00:00+00:00",
  "data": { ... }
}
```

> **Tip:** Use [https://webhook.site](https://webhook.site) to get a free listener URL for testing — paste it as the `url` when registering a webhook, then use the `/test` endpoint to verify connectivity before waiting for real events.

---

## How Caching Works

```
Incoming redirect request
        │
        ▼
  Redis lookup (url_shortcode:<code>)
        │
   Hit ─┼─ Miss
        │         │
        ▼         ▼
   Redirect    DB lookup
                  │
              Found ─┬─ Not Found → 404
                     │
              Write to Redis (TTL 1 hr)
                     │
                     ▼
                 Redirect
```

- Cache keys are namespaced: `url_shortcode:{short_code}`
- TTL defaults to **1 hour** on write-through; **5 minutes** on direct `set_cache` calls
- Deleting a URL also evicts its cache entry

---

## How Webhooks Work

```
URL event (create / click / delete)
        │
        ▼
  fire_event() called from route handler
        │
        ▼
  Load active webhooks subscribed to this event
        │
        ▼
  asyncio.create_task(_deliver(...))  ← non-blocking, fire-and-forget
        │
        ▼
  API response returns immediately
        │           │
        │           ▼ (background)
        │     POST JSON payload to each target URL
        │     Errors are logged, never propagated
```

- Delivery is **fire-and-forget** — the API response is never delayed by webhook calls
- Delivery errors are logged but do not affect the API caller
- Each POST includes `Content-Type: application/json` and `X-Webhook-Event` headers

---

## Alembic — Database Migrations

Alembic is configured for **async** SQLAlchemy (asyncpg). Always run these from the project root.

```bash
# Generate a migration by comparing your models to the actual database
alembic revision --autogenerate -m "create urls table"

# Apply all pending migrations — brings the DB up to date
alembic upgrade head

# Roll back the last migration — undo the most recent change
alembic downgrade -1

# Check what migration the database is currently at
alembic current

# View the full migration history
alembic history --verbose

# Show pending migrations (what upgrade head would apply)
alembic history -r current:head
```

### First-time migration workflow

```bash
# 1. Autogenerate the initial migration from your models
alembic revision --autogenerate -m "initial schema"

# 2. Review the generated file in alembic/versions/ before applying
# 3. Apply it
alembic upgrade head
```

> **Always review autogenerated migrations** before running them — Alembic may miss some changes (e.g. renamed columns, custom constraints).

---

## Running in Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Interactive docs are available at [http://localhost:8000/docs](http://localhost:8000/docs) when the server is running.

Set `echo=True` on the engine in `database.py` only for debugging — it logs every SQL query.
