# Lyftr Backend Assignment --- Webhook Ingestion API

A FastAPI-based backend service for ingesting webhook messages,
verifying HMAC signatures, storing messages idempotently, and exposing
analytics and query endpoints.

-----------------

## Features

-   HMAC SHA256 signature verification
-   Idempotent webhook ingestion
-   SQLite persistence
-   Structured JSON request logging
-   Health check endpoints
-   Message listing with pagination and filters
-   Analytics stats endpoint
-   Fully Dockerized setup

----------------------

## Architecture

-   **FastAPI** --- API framework
-   **SQLite** --- persistence layer
-   **aiosqlite** --- async DB client
-   **Docker Compose** --- local orchestration
-   **Middleware logging** --- JSON structured logs to stdout

-----------------------
## Environment Variables

Create a `.env` file in the project root:

``` env
WEBHOOK_SECRET=testsecret
DATABASE_URL=sqlite:////data/app.db
```

A template is provided in `.env.example`.

-----------------------

## Run Locally

Build and start the service:

``` bash
docker compose up -d --build
```

Verify health:

``` bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

----------------

## Webhook Endpoint

**POST** `/webhook`

### Headers

    Content-Type: application/json
    X-Signature: <hex sha256 signature>

### Example Request

``` bash
curl -X POST http://localhost:8000/webhook   -H "Content-Type: application/json"   -H "X-Signature: <signature>"   -d '{
    "message_id":"m1",
    "from":"+919876543210",
    "to":"+14155550100",
    "ts":"2025-01-15T10:00:00Z",
    "text":"Hello"
  }'
```

### Behavior

-   Invalid signature → **401 Unauthorized**
-   Duplicate `message_id` → **200 OK** (idempotent)
-   Valid new message → stored

----------------------

## List Messages

**GET** `/messages`

### Query Parameters

  Name       Description
  ---------- ------------------------------------------------
  `limit`    1--100
  `offset`   ≥ 0
  `from`     Sender MSISDN (URL encoded, e.g. `%2B9198...`)
  `since`    ISO-8601 UTC timestamp
  `q`        Free-text search in message body

### Example

``` bash
curl "http://localhost:8000/messages?limit=10&offset=0"
```

-------------------

## Stats Endpoint

**GET** `/stats`

Returns aggregate analytics:

``` json
{
  "total_messages": 2,
  "senders_count": 2,
  "messages_per_sender": [
    {"from":"+919876543210","count":1}
  ],
  "first_message_ts":"2025-01-15T09:00:00Z",
  "last_message_ts":"2025-01-15T10:00:00Z"
}
```

----------------------

## Structured Logging

Each request emits a JSON log line:

``` json
{
  "ts": "2026-01-28T04:04:33Z",
  "level": "INFO",
  "request_id": "uuid",
  "method": "POST",
  "path": "/webhook",
  "status": 200,
  "latency_ms": 12,
  "result": "created",
  "message_id": "m1",
  "dup": false
}
```

-------------------

## Suggested Manual Tests

-   Health endpoints
-   Invalid webhook signature
-   Duplicate message insert
-   Pagination
-   Filtering by sender
-   Stats aggregates

-------------------

## Cleanup

Stop containers and remove volumes:

``` bash
docker compose down -v
```

-----------------

## Author

Kunal Sharma
