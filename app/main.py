from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import hmac
import hashlib
import re
import os
import aiosqlite

from app.config import settings
from app.models import init_db
from app.storage import insert_message


app = FastAPI(title="Lyftr Webhook API")


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

    return {"status": "ok"}
