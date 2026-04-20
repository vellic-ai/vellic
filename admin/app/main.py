import logging
import os

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("admin")

app = FastAPI(title="vellic-admin", version="0.1.0")


@app.on_event("startup")
async def startup() -> None:
    logger.info("vellic admin starting on port %s", os.getenv("PORT", "8001"))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "admin"}


@app.post("/admin/replay/{delivery_id}")
async def replay_delivery(delivery_id: str) -> dict:
    # Stub — re-enqueues stored webhook payload for replay
    return {"status": "queued", "delivery_id": delivery_id}
