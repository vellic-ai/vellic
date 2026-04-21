import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import arq_pool, db
from .features_router import router as features_router
from .llm_config_router import router as llm_config_router
from .repos_router import router as repos_router
from .webhook import router as webhook_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("vellic api starting on port %s", os.getenv("PORT", "8000"))
    await db.init_pool()
    await arq_pool.init_pool()
    yield
    await arq_pool.close_pool()
    await db.close_pool()


app = FastAPI(title="vellic-api", version="0.1.0", lifespan=lifespan)
app.include_router(webhook_router)
app.include_router(features_router)
app.include_router(repos_router)
app.include_router(llm_config_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "api"}
