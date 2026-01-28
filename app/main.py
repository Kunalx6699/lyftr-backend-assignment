from fastapi import FastAPI, HTTPException, Request, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import hmac
import hashlib
import re
import os
import aiosqlite
import time
import uuid

from app.config import settings
from app.models import init_db
from app.storage import insert_message, list_messages, get_stats
from app.logging_utils import log_event


app = FastAPI(title="Lyftr Webhook API")


# Logging Middleware


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.time()

    request.state.request_id = request_id

    response = await call_next(request)

    latency_ms = int((time.time() - start) * 1000)

    log_event(
        level="INFO",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=latency_ms,
    )

    return response



# Startup / Health


@app.on_event("startup")
async def startup():
    if not settings.WEBHOOK_SECRET:
        raise RuntimeError("WEBHOOK_SECRET not set")

    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    await init_db(db_path)


@app.get("/health/live")
async def live():
    return {"status": "ok"}


@app.get("/health/ready")
async def ready():
    try:
        if not settings.WEBHOOK_SECRET:
            raise RuntimeError("secret missing")

        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        async with aiosqlite.connect(db_path) as db:
            await db.execute("SELECT 1")

        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="not ready")



# Webhook Validation


E164_REGEX = re.compile(r"^\+[1-9]\d{1,14}$")


class WebhookMessage(BaseModel):
    message_id: str = Field(..., min_length=1)
    from_: str = Field(..., alias="from")
    to: str
    ts: str
    text: str | None = Field(default=None, max_length=4096)

    @validator("from_", "to")
    def validate_e164(cls, v):
        if not E164_REGEX.match(v):
            raise ValueError("must be in E.164 format")
        return v

    @validator("ts")
    def validate_ts(cls, v):
        if not v.endswith("Z"):
            raise ValueError("must be UTC Z timestamp")
        return v


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    computed = hmac.new(
        key=secret.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, signature)

@app.get("/stats")
async def stats():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")

    return await get_stats(db_path)


# Webhook Endpoint


@app.post("/webhook")
async def webhook(
    request: Request,
    payload: WebhookMessage,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
):
    raw_body = await request.body()

    # Signature validation FIRST
    if not x_signature or not verify_signature(
        settings.WEBHOOK_SECRET, raw_body, x_signature
    ):
        log_event(
            level="ERROR",
            request_id=request.state.request_id,
            method="POST",
            path="/webhook",
            status=401,
            latency_ms=0,
            result="invalid_signature",
            message_id=payload.message_id if payload else None,
            dup=False,
        )

        return JSONResponse(
            status_code=401,
            content={"detail": "invalid signature"},
        )

    db_path = settings.DATABASE_URL.replace("sqlite:///", "")

    inserted = await insert_message(
        db_path,
        {
            "message_id": payload.message_id,
            "from": payload.from_,
            "to": payload.to,
            "ts": payload.ts,
            "text": payload.text,
        },
    )

    result = "created" if inserted else "duplicate"

    log_event(
        level="INFO",
        request_id=request.state.request_id,
        method="POST",
        path="/webhook",
        status=200,
        latency_ms=0,
        result=result,
        message_id=payload.message_id,
        dup=not inserted,
    )

    return {"status": "ok"}



# Messages Endpoint


@app.get("/messages")
async def get_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_: str | None = Query(default=None, alias="from"),
    since: str | None = None,
    q: str | None = None,
):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")

    data, total = await list_messages(
        db_path=db_path,
        limit=limit,
        offset=offset,
        from_filter=from_,
        since=since,
        q=q,
    )

    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
