from fastapi import FastAPI

app = FastAPI(title="Lyftr Webhook API")

@app.get("/health/live")
async def live():
    return {"status": "ok"}