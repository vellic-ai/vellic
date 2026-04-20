import json
import logging
import uuid

import asyncpg
from arq import Retry

from .adapters.github import normalize_pr
from .llm.protocol import LLMProvider
from .pipeline.feedback_poster import GitHubClientError, RateLimitError, post_github_review
from .pipeline.models import AnalysisResult, ReviewComment
from .pipeline.runner import run_pipeline

logger = logging.getLogger("worker.jobs")

# Backoff delays between attempt N and N+1 (seconds): 5s → 25s → dead-letter
_RETRY_DELAYS = [5, 25]
# Backoff for post_feedback rate-limit / 5xx retries (seconds)
_FEEDBACK_RETRY_DELAYS = [60, 300]


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

    event = normalize_pr(delivery_id, payload)
    job_id = await _get_or_create_job(pool, delivery_id)

    try:
        await run_pipeline(event, pool, llm, job_id, arq_redis)
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


async def post_feedback(ctx: dict, pr_review_id: str) -> None:
    """Post analysis feedback to GitHub as a PR review."""
    pool: asyncpg.Pool = ctx["db_pool"]
    job_try: int = ctx.get("job_try", 1)

    row = await pool.fetchrow(
        "SELECT repo, pr_number, commit_sha, feedback, github_review_id FROM pr_reviews WHERE id = $1",
        uuid.UUID(pr_review_id),
    )
    if row is None:
        logger.warning("pr_review %s not found — skipping post_feedback", pr_review_id)
        return

    if row["github_review_id"] is not None:
        logger.info("pr_review %s already posted (github_review_id=%s) — skipping dedup", pr_review_id, row["github_review_id"])
        return

    feedback: dict = row["feedback"]
    result = AnalysisResult(
        comments=[
            ReviewComment(
                file=c["file"],
                line=int(c["line"]),
                body=c["body"],
                confidence=float(c["confidence"]),
                rationale=c.get("rationale", ""),
            )
            for c in feedback.get("comments", [])
        ],
        summary=feedback.get("summary", ""),
        generic_ratio=float(feedback.get("generic_ratio", 0.0)),
    )

    try:
        github_review_id = await post_github_review(
            repo=row["repo"],
            pr_number=row["pr_number"],
            commit_sha=row["commit_sha"],
            result=result,
        )
    except RateLimitError as exc:
        logger.warning("rate limit hit for pr_review=%s attempt=%d: %s", pr_review_id, job_try, exc)
        if job_try >= len(_FEEDBACK_RETRY_DELAYS) + 1:
            logger.error("rate limit retry exhausted for pr_review=%s", pr_review_id)
            raise
        delay = _FEEDBACK_RETRY_DELAYS[min(job_try - 1, len(_FEEDBACK_RETRY_DELAYS) - 1)]
        raise Retry(defer_by=delay) from exc
    except GitHubClientError as exc:
        logger.error("terminal GitHub error for pr_review=%s: %s", pr_review_id, exc)
        return
    except Exception as exc:
        logger.warning("post_feedback error attempt=%d for pr_review=%s: %s", job_try, pr_review_id, exc)
        if job_try >= 3:
            logger.error("post_feedback retries exhausted for pr_review=%s", pr_review_id)
            raise
        delay = _FEEDBACK_RETRY_DELAYS[min(job_try - 1, len(_FEEDBACK_RETRY_DELAYS) - 1)]
        raise Retry(defer_by=delay) from exc

    await pool.execute(
        "UPDATE pr_reviews SET github_review_id = $1, posted_at = NOW() WHERE id = $2",
        github_review_id,
        uuid.UUID(pr_review_id),
    )
    logger.info(
        "posted GitHub review=%s for pr_review=%s repo=%s pr=%d",
        github_review_id,
        pr_review_id,
        row["repo"],
        row["pr_number"],
    )
