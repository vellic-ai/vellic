import json
import logging
import uuid

import asyncpg
from arq.exceptions import Retry

from .llm.protocol import LLMProvider
from .pipeline.runner import run_pipeline

logger = logging.getLogger("worker.jobs")

# Backoff delays between attempt N and N+1 (seconds): 5s → 25s → dead-letter
_RETRY_DELAYS = [5, 25]


async def _get_or_create_job(pool: asyncpg.Pool, delivery_id: str) -> uuid.UUID:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM pipeline_jobs WHERE delivery_id = $1 ORDER BY created_at DESC LIMIT 1",
            delivery_id,
        )
        if row is None:
            row = await conn.fetchrow(
                "INSERT INTO pipeline_jobs (delivery_id, status) VALUES ($1, 'running') RETURNING id",
                delivery_id,
            )
        else:
            await conn.execute(
                """
                UPDATE pipeline_jobs
                SET status = 'running', retry_count = retry_count + 1, updated_at = NOW()
                WHERE id = $1
                """,
                row["id"],
            )
        return row["id"]


async def _dead_letter(
    pool: asyncpg.Pool,
    job_id: uuid.UUID,
    delivery_id: str,
    payload: dict,
    exc: Exception,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE pipeline_jobs SET status = 'failed', updated_at = NOW() WHERE id = $1",
            job_id,
        )
        await conn.execute(
            """
            INSERT INTO pipeline_failures (job_id, payload, error)
            VALUES ($1, $2::jsonb, $3)
            """,
            job_id,
            json.dumps({"delivery_id": delivery_id, "payload": payload}),
            str(exc),
        )
    logger.error("dead-letter: job_id=%s delivery=%s error=%s", job_id, delivery_id, exc)


async def process_webhook(ctx: dict, delivery_id: str) -> None:
    pool: asyncpg.Pool = ctx["db_pool"]
    llm: LLMProvider = ctx["llm"]
    arq_redis = ctx["redis"]
    job_try: int = ctx.get("job_try", 1)

    row = await pool.fetchrow(
        "SELECT event_type, payload FROM webhook_deliveries WHERE delivery_id = $1",
        delivery_id,
    )
    if row is None:
        logger.warning("delivery %s not found — skipping", delivery_id)
        return

    event_type: str = row["event_type"]
    payload: dict = row["payload"]
    logger.info("delivery=%s event=%s attempt=%d", delivery_id, event_type, job_try)

    if event_type != "pull_request":
        await pool.execute(
            "UPDATE webhook_deliveries SET processed_at = NOW() WHERE delivery_id = $1",
            delivery_id,
        )
        logger.info("non-PR event %s — marked processed", event_type)
        return

    job_id = await _get_or_create_job(pool, delivery_id)

    try:
        await run_pipeline(payload, pool, llm, job_id, arq_redis)
        await pool.execute(
            "UPDATE webhook_deliveries SET processed_at = NOW() WHERE delivery_id = $1",
            delivery_id,
        )
    except Exception as exc:
        logger.warning("pipeline error attempt=%d: %s", job_try, exc)
        if job_try >= 3:
            await _dead_letter(pool, job_id, delivery_id, payload, exc)
            raise
        delay = _RETRY_DELAYS[job_try - 1]
        logger.info("scheduling retry in %ds", delay)
        raise Retry(defer_by=delay) from exc
