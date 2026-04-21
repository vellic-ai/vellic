import json
import logging
import uuid

import asyncpg
from arq import Retry

from .adapters.github import normalize_pr
from .adapters.gitlab import normalize_mr
from .llm import build_provider
from .llm.config import _EXTERNAL_PROVIDERS, load_env_llm_config
from .llm.db_config import load_llm_config_from_db
from .metrics import (
    compute_retry_delays,
    get_max_retries,
    get_retry_base_delay,
    webhook_dlq_depth,
    webhook_retry_total,
)
from .pipeline.feedback_poster import (
    GitHubClientError,
    GitLabClientError,
    RateLimitError,
    post_github_review,
    post_gitlab_discussion,
)
from .pipeline.models import AnalysisResult, ReviewComment
from .pipeline.runner import run_pipeline

logger = logging.getLogger("worker.jobs")

_EXTERNAL_PROVIDER_WARNING = (
    "⚠️  External LLM provider active. "
    "PR diff content will leave your infrastructure."
)

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
                "INSERT INTO pipeline_jobs (delivery_id, status)"
                " VALUES ($1, 'running') RETURNING id",
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
    retry_count: int = 0,
) -> None:
    error_str = str(exc)
    async with pool.acquire() as conn:
        async with conn.transaction():
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
                error_str,
            )
            await conn.execute(
                """
                INSERT INTO webhook_dlq
                    (delivery_id, job_id, payload, last_error, retry_count, last_attempted_at)
                VALUES ($1, $2, $3::jsonb, $4, $5, NOW())
                ON CONFLICT (delivery_id) DO UPDATE SET
                    job_id            = EXCLUDED.job_id,
                    last_error        = EXCLUDED.last_error,
                    retry_count       = EXCLUDED.retry_count,
                    last_attempted_at = EXCLUDED.last_attempted_at,
                    status            = 'pending'
                """,
                delivery_id,
                job_id,
                json.dumps(payload),
                error_str,
                retry_count,
            )
        pending_count = await conn.fetchval(
            "SELECT COUNT(*) FROM webhook_dlq WHERE status = 'pending'"
        )
    webhook_dlq_depth.set(pending_count)
    logger.error(
        "dead-letter: job_id=%s delivery=%s retries=%d error=%s",
        job_id,
        delivery_id,
        retry_count,
        exc,
    )


async def _get_repo_installation(
    pool: asyncpg.Pool, platform: str, org: str, repo: str
) -> dict | None:
    """Return the most-specific matching installation row, or None if no rows exist."""
    rows = await pool.fetch(
        """
        SELECT config_json FROM installations
        WHERE platform = $1 AND org = $2
          AND (repo = $3 OR repo IS NULL)
        ORDER BY (repo = $3) DESC NULLS LAST
        LIMIT 1
        """,
        platform,
        org,
        repo,
    )
    if not rows:
        return None
    return dict(rows[0])


async def process_webhook(ctx: dict, delivery_id: str) -> None:
    pool: asyncpg.Pool = ctx["db_pool"]
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

    if event_type not in ("pull_request", "merge_request", "Merge Request Hook"):
        await pool.execute(
            "UPDATE webhook_deliveries SET processed_at = NOW() WHERE delivery_id = $1",
            delivery_id,
        )
        logger.info("non-MR event %s — marked processed", event_type)
        return

    # Determine platform and extract repo path.
    is_gitlab = event_type in ("merge_request", "Merge Request Hook")
    if is_gitlab:
        repo_full = (payload.get("project") or {}).get("path_with_namespace", "")
        platform = "gitlab"
    else:
        repo_full = (payload.get("repository") or {}).get("full_name", "")
        platform = "github"

    # Check repo allow-list; apply per-repo LLM overrides if present.
    installation_cfg: dict = {}
    if repo_full:
        org_part, _, repo_part = repo_full.partition("/")
        inst = await _get_repo_installation(pool, platform, org_part, repo_part)
        if inst is not None:
            installation_cfg = inst.get("config_json") or {}
            if not installation_cfg.get("enabled", True):
                logger.info("repo %s disabled — skipping delivery %s", repo_full, delivery_id)
                await pool.execute(
                    "UPDATE webhook_deliveries SET processed_at = NOW() WHERE delivery_id = $1",
                    delivery_id,
                )
                return

    # Load LLM config: DB row takes precedence; fall back to env vars.
    try:
        cfg = await load_llm_config_from_db(pool)
    except Exception as exc:
        logger.warning("failed to load LLM config from DB, falling back to env vars: %s", exc)
        cfg = None
    if cfg is None:
        cfg = load_env_llm_config()
        logger.info("llm config: using env-var fallback (no DB row)")
    else:
        logger.info(
            "llm config: loaded from DB provider=%s model=%s", cfg["provider"], cfg["model"]
        )

    # Per-repo provider/model override.
    if installation_cfg.get("provider") and installation_cfg.get("model"):
        cfg = {**cfg, "provider": installation_cfg["provider"], "model": installation_cfg["model"]}
        logger.info(
            "per-repo llm override provider=%s model=%s for %s",
            cfg["provider"],
            cfg["model"],
            repo_full,
        )

    if cfg["provider"] in _EXTERNAL_PROVIDERS:
        logger.warning(_EXTERNAL_PROVIDER_WARNING)

    llm = build_provider(
        cfg["provider"],
        base_url=cfg.get("base_url", ""),
        model=cfg["model"],
        api_key=cfg.get("api_key", ""),
        bin_path=cfg.get("bin_path", "claude"),
    )

    event = normalize_mr(delivery_id, payload) if is_gitlab else normalize_pr(delivery_id, payload)
    job_id = await _get_or_create_job(pool, delivery_id)

    max_retries = get_max_retries()
    base_delay = get_retry_base_delay()
    retry_delays = compute_retry_delays(max_retries, base_delay)
    # job_try=1 is the initial attempt; retries start at job_try=2
    max_attempts = max_retries + 1

    try:
        await run_pipeline(event, pool, llm, job_id, arq_redis)
        await pool.execute(
            "UPDATE webhook_deliveries SET processed_at = NOW() WHERE delivery_id = $1",
            delivery_id,
        )
    except Exception as exc:
        logger.warning("pipeline error attempt=%d/%d: %s", job_try, max_attempts, exc)
        if job_try >= max_attempts:
            await _dead_letter(pool, job_id, delivery_id, payload, exc, retry_count=job_try - 1)
            raise
        webhook_retry_total.inc()
        delay = retry_delays[job_try - 1]
        logger.info("scheduling retry in %ds (attempt %d/%d)", delay, job_try + 1, max_attempts)
        raise Retry(defer=delay) from exc


async def post_feedback(ctx: dict, pr_review_id: str) -> None:
    """Post analysis feedback to the appropriate VCS platform."""
    pool: asyncpg.Pool = ctx["db_pool"]
    job_try: int = ctx.get("job_try", 1)

    row = await pool.fetchrow(
        "SELECT repo, pr_number, commit_sha, feedback, platform,"
        " github_review_id, gitlab_discussion_id"
        " FROM pr_reviews WHERE id = $1",
        uuid.UUID(pr_review_id),
    )
    if row is None:
        logger.warning("pr_review %s not found — skipping post_feedback", pr_review_id)
        return

    platform = row["platform"] or "github"

    # Dedup: skip if already posted for this platform.
    if platform == "gitlab" and row["gitlab_discussion_id"] is not None:
        logger.info(
            "pr_review %s already posted (gitlab_discussion_id=%s) — skipping dedup",
            pr_review_id,
            row["gitlab_discussion_id"],
        )
        return
    if platform == "github" and row["github_review_id"] is not None:
        logger.info(
            "pr_review %s already posted (github_review_id=%s) — skipping dedup",
            pr_review_id,
            row["github_review_id"],
        )
        return
    if platform == "bitbucket" and row["bitbucket_comment_id"] is not None:
        logger.info(
            "pr_review %s already posted (bitbucket_comment_id=%s) — skipping dedup",
            pr_review_id,
            row["bitbucket_comment_id"],
        )
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
        if platform == "gitlab":
            platform_id = await post_gitlab_discussion(
                repo=row["repo"],
                mr_iid=row["pr_number"],
                commit_sha=row["commit_sha"],
                result=result,
            )
            id_col = "gitlab_discussion_id"
            dedup_clause = "AND gitlab_discussion_id IS NULL"
        else:
            platform_id = await post_github_review(
                repo=row["repo"],
                pr_number=row["pr_number"],
                commit_sha=row["commit_sha"],
                result=result,
            )
            id_col = "github_review_id"
            dedup_clause = "AND github_review_id IS NULL"
    except RateLimitError as exc:
        logger.warning("rate limit hit for pr_review=%s attempt=%d: %s", pr_review_id, job_try, exc)
        if job_try >= len(_FEEDBACK_RETRY_DELAYS) + 1:
            logger.error("rate limit retry exhausted for pr_review=%s", pr_review_id)
            raise
        delay = _FEEDBACK_RETRY_DELAYS[min(job_try - 1, len(_FEEDBACK_RETRY_DELAYS) - 1)]
        raise Retry(defer=delay) from exc
    except (GitHubClientError, GitLabClientError) as exc:
        logger.error("terminal %s error for pr_review=%s: %s", platform, pr_review_id, exc)
        return
    except Exception as exc:
        logger.warning(
            "post_feedback error attempt=%d for pr_review=%s: %s", job_try, pr_review_id, exc
        )
        if job_try >= 3:
            logger.error("post_feedback retries exhausted for pr_review=%s", pr_review_id)
            raise
        delay = _FEEDBACK_RETRY_DELAYS[min(job_try - 1, len(_FEEDBACK_RETRY_DELAYS) - 1)]
        raise Retry(defer=delay) from exc

    updated = await pool.fetchval(
        f"UPDATE pr_reviews SET {id_col} = $1, posted_at = NOW() "
        f"WHERE id = $2 {dedup_clause} RETURNING id",
        platform_id,
        uuid.UUID(pr_review_id),
    )
    if updated is None:
        logger.info("pr_review %s already posted by concurrent worker — skipping", pr_review_id)
        return
    logger.info(
        "posted %s review=%s for pr_review=%s repo=%s mr=%d",
        platform,
        platform_id,
        pr_review_id,
        row["repo"],
        row["pr_number"],
    )
