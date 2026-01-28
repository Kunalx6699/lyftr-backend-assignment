from fastapi import FastAPI, HTTPException
from app.config import settings
from app.models import init_db
import aiosqlite
import os

app = FastAPI(title="Lyftr Webhook API")

import os

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
