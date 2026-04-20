import logging
import uuid

import asyncpg

from ..events import PREvent
from ..llm.protocol import LLMProvider
from .context_gatherer import gather_context
from .diff_fetcher import fetch_diff_chunks
from .llm_analyzer import analyze
from .result_persister import persist

logger = logging.getLogger("worker.pipeline.runner")


async def run_pipeline(
    event: PREvent,
    pool: asyncpg.Pool,
    llm: LLMProvider,
    job_id: uuid.UUID,
    arq_redis,
) -> str:
    context = gather_context(event)
    logger.info("pipeline start repo=%s pr=%d sha=%s", context.repo, context.pr_number, context.commit_sha)

    chunks = await fetch_diff_chunks(event.diff_url)
    logger.info("stage1 complete chunks=%d", len(chunks))

    result = await analyze(context, chunks, llm)
    logger.info(
        "stage3 complete comments=%d generic_ratio=%.2f",
        len(result.comments),
        result.generic_ratio,
    )

    pr_review_id = await persist(pool, context, result, job_id, arq_redis)
    logger.info("stage4 complete pr_review_id=%s", pr_review_id)
    return pr_review_id
