import dataclasses
import json
import logging
import uuid

import asyncpg

from .models import AnalysisResult, PRContext

logger = logging.getLogger("worker.pipeline.result_persister")


async def persist(
    pool: asyncpg.Pool,
    context: PRContext,
    result: AnalysisResult,
    job_id: uuid.UUID,
    arq_redis,
) -> str:
    """Persist analysis to pr_reviews; enqueue post_feedback job. Returns pr_review_id."""
    feedback_json = json.dumps(
        {
            "comments": [dataclasses.asdict(c) for c in result.comments],
            "summary": result.summary,
            "generic_ratio": result.generic_ratio,
        }
    )

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO pr_reviews (repo, pr_number, commit_sha, feedback)
            VALUES ($1, $2, $3, $4::jsonb)
            ON CONFLICT ON CONSTRAINT uq_pr_reviews_repo_pr_sha
                DO UPDATE SET feedback = EXCLUDED.feedback
            RETURNING id
            """,
            context.repo,
            context.pr_number,
            context.commit_sha,
            feedback_json,
        )
        pr_review_id: uuid.UUID = row["id"]

        await conn.execute(
            "UPDATE pipeline_jobs SET status = 'done', updated_at = NOW() WHERE id = $1",
            job_id,
        )

    await arq_redis.enqueue_job("post_feedback", str(pr_review_id))
    logger.info(
        "persisted pr_review=%s enqueued post_feedback for %s#%d",
        pr_review_id,
        context.repo,
        context.pr_number,
    )
    return str(pr_review_id)
