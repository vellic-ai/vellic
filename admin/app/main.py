import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException

from . import arq_pool, db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("admin")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("vellic admin starting on port %s", os.getenv("PORT", "8001"))
    await db.init_pool()
    await arq_pool.init_pool()
    yield
    await arq_pool.close_pool()
    await db.close_pool()


app = FastAPI(title="vellic-admin", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "admin"}


@app.post("/admin/replay/{delivery_id}", status_code=202)
async def replay_delivery(delivery_id: str) -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT delivery_id, event_type FROM webhook_deliveries WHERE delivery_id = $1",
            delivery_id,
        )

    if row is None:
        raise HTTPException(status_code=404, detail=f"delivery {delivery_id!r} not found")

    arq = arq_pool.get_pool()
    await arq.enqueue_job("process_webhook", delivery_id)
    logger.info("replayed delivery=%s event=%s", delivery_id, row["event_type"])

    return {"status": "queued", "delivery_id": delivery_id, "event_type": row["event_type"]}
