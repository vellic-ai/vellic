import logging

import asyncpg

from .llm.protocol import LLMProvider

logger = logging.getLogger("worker.jobs")


async def process_webhook(ctx: dict, delivery_id: str) -> None:
    pool: asyncpg.Pool = ctx["db_pool"]
    llm: LLMProvider = ctx["llm"]

    row = await pool.fetchrow(
        "SELECT delivery_id, event_type, payload FROM webhook_deliveries WHERE delivery_id = $1",
        delivery_id,
    )
    if row is None:
        logger.warning("delivery %s not found in db — skipping", delivery_id)
        return

    logger.info("processing delivery=%s event=%s", delivery_id, row["event_type"])

    healthy = await llm.health()
    if not healthy:
        logger.warning("LLM provider unhealthy — skipping inference for delivery=%s", delivery_id)

    # LLM review pipeline wired in subsequent sprint (VEL-21+)

    await pool.execute(
        "UPDATE webhook_deliveries SET processed_at = NOW() WHERE delivery_id = $1",
        delivery_id,
    )
    logger.info("delivery=%s marked processed", delivery_id)
