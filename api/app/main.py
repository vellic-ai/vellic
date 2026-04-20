import logging
import os

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("api")

app = FastAPI(title="vellic-api", version="0.1.0")


@app.on_event("startup")
async def startup() -> None:
    logger.info("vellic api starting on port %s", os.getenv("PORT", "8000"))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "api"}


@app.post("/webhook/github")
async def github_webhook() -> dict:
    # Stub — full implementation in VEL Sprint 1
    return {"status": "accepted"}
