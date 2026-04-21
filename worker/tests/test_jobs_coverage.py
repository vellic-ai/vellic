"""Tests for uncovered branches in worker/app/jobs.py.

Covers:
- _get_or_create_job (both branches: existing vs new row)
- _dead_letter
- process_webhook (multiple paths)
- post_feedback (not-found path, rate-limit retry, GitHubClientError terminal path)
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq import Retry

from app.jobs import _dead_letter, _get_or_create_job, post_feedback, process_webhook
from app.pipeline.feedback_poster import GitHubClientError, RateLimitError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool_with_conn(conn):
    pool = MagicMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=False),
        )
    )
    return pool


_PR_PAYLOAD = {
    "action": "opened",
    "repository": {"full_name": "acme/backend"},
    "pull_request": {
        "number": 1,
        "head": {"sha": "hsha"},
        "base": {"sha": "bsha", "ref": "main"},
        "title": "feat",
        "body": "",
        "diff_url": "https://github.com/acme/backend/pull/1.diff",
    },
}


# ---------------------------------------------------------------------------
# _get_or_create_job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_job_returns_existing_id():
    existing_id = uuid.uuid4()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": existing_id},  # SELECT — row found
        ]
    )
    conn.execute = AsyncMock()
    pool = _make_pool_with_conn(conn)

    result = await _get_or_create_job(pool, "del-1")

    assert result == existing_id
    conn.execute.assert_called_once()  # UPDATE retry_count


@pytest.mark.asyncio
async def test_get_or_create_job_inserts_when_missing():
    new_id = uuid.uuid4()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            None,              # SELECT — not found
            {"id": new_id},   # INSERT RETURNING
        ]
    )
    pool = _make_pool_with_conn(conn)

    result = await _get_or_create_job(pool, "del-new")

    assert result == new_id
    assert conn.fetchrow.call_count == 2


# ---------------------------------------------------------------------------
# _dead_letter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dead_letter_executes_two_queries():
    conn = AsyncMock()
    conn.execute = AsyncMock()
    pool = _make_pool_with_conn(conn)
    job_id = uuid.uuid4()

    with patch("app.jobs.webhook_dlq_depth"):
        await _dead_letter(pool, job_id, "del-1", {"action": "opened"}, ValueError("boom"))

    # pipeline_jobs update + pipeline_failures insert + webhook_dlq upsert
    assert conn.execute.call_count == 3


# ---------------------------------------------------------------------------
# process_webhook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_webhook_skips_when_delivery_not_found():
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=None)
    ctx = {"db_pool": pool, "redis": AsyncMock(), "job_try": 1}

    await process_webhook(ctx, "missing-delivery")

    pool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_process_webhook_marks_processed_for_non_pr_event():
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(
        return_value={"event_type": "push", "payload": {"repository": {"full_name": "acme/backend"}}}
    )
    pool.execute = AsyncMock()
    ctx = {"db_pool": pool, "redis": AsyncMock(), "job_try": 1}

    await process_webhook(ctx, "del-push")

    pool.execute.assert_called_once()
    sql = pool.execute.call_args[0][0]
    assert "processed_at" in sql


@pytest.mark.asyncio
async def test_process_webhook_skips_disabled_repo():
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(
        return_value={"event_type": "pull_request", "payload": _PR_PAYLOAD}
    )
    pool.execute = AsyncMock()
    ctx = {"db_pool": pool, "redis": AsyncMock(), "job_try": 1}

    with patch(
        "app.jobs._get_repo_installation",
        new=AsyncMock(return_value={"config_json": {"enabled": False}}),
    ):
        await process_webhook(ctx, "del-disabled")

    pool.execute.assert_called_once()
    sql = pool.execute.call_args[0][0]
    assert "processed_at" in sql


@pytest.mark.asyncio
async def test_process_webhook_happy_path():
    job_id = uuid.uuid4()
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(
        return_value={"event_type": "pull_request", "payload": _PR_PAYLOAD}
    )
    pool.execute = AsyncMock()

    with (
        patch("app.jobs._get_repo_installation", new=AsyncMock(return_value=None)),
        patch("app.jobs.load_llm_config_from_db", new=AsyncMock(return_value=None)),
        patch("app.jobs.load_env_llm_config", return_value={"provider": "ollama", "model": "llama3", "base_url": "http://localhost", "api_key": ""}),
        patch("app.jobs.build_provider", return_value=MagicMock()),
        patch("app.jobs._get_or_create_job", new=AsyncMock(return_value=job_id)),
        patch("app.jobs.run_pipeline", new=AsyncMock(return_value="rev-1")),
    ):
        ctx = {"db_pool": pool, "redis": AsyncMock(), "job_try": 1}
        await process_webhook(ctx, "del-ok")

    pool.execute.assert_called_once()
    sql = pool.execute.call_args[0][0]
    assert "processed_at" in sql


@pytest.mark.asyncio
async def test_process_webhook_retries_on_pipeline_error():
    job_id = uuid.uuid4()
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(
        return_value={"event_type": "pull_request", "payload": _PR_PAYLOAD}
    )
    pool.execute = AsyncMock()

    with (
        patch("app.jobs._get_repo_installation", new=AsyncMock(return_value=None)),
        patch("app.jobs.load_llm_config_from_db", new=AsyncMock(return_value=None)),
        patch("app.jobs.load_env_llm_config", return_value={"provider": "ollama", "model": "m", "base_url": "", "api_key": ""}),
        patch("app.jobs.build_provider", return_value=MagicMock()),
        patch("app.jobs._get_or_create_job", new=AsyncMock(return_value=job_id)),
        patch("app.jobs.run_pipeline", new=AsyncMock(side_effect=RuntimeError("transient"))),
    ):
        ctx = {"db_pool": pool, "redis": AsyncMock(), "job_try": 1}
        with pytest.raises(Retry):
            await process_webhook(ctx, "del-retry")


@pytest.mark.asyncio
async def test_process_webhook_dead_letters_on_third_attempt():
    job_id = uuid.uuid4()
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(
        return_value={"event_type": "pull_request", "payload": _PR_PAYLOAD}
    )
    pool.execute = AsyncMock()

    with (
        patch("app.jobs._get_repo_installation", new=AsyncMock(return_value=None)),
        patch("app.jobs.load_llm_config_from_db", new=AsyncMock(return_value=None)),
        patch("app.jobs.load_env_llm_config", return_value={"provider": "ollama", "model": "m", "base_url": "", "api_key": ""}),
        patch("app.jobs.build_provider", return_value=MagicMock()),
        patch("app.jobs._get_or_create_job", new=AsyncMock(return_value=job_id)),
        patch("app.jobs.run_pipeline", new=AsyncMock(side_effect=RuntimeError("fatal"))),
        patch("app.jobs._dead_letter", new=AsyncMock()) as mock_dl,
        patch("app.jobs.get_max_retries", return_value=2),
        patch("app.jobs.get_retry_base_delay", return_value=5),
    ):
        ctx = {"db_pool": pool, "redis": AsyncMock(), "job_try": 3}
        with pytest.raises(RuntimeError, match="fatal"):
            await process_webhook(ctx, "del-dead")

    mock_dl.assert_called_once()


@pytest.mark.asyncio
async def test_process_webhook_loads_db_llm_config_when_available():
    job_id = uuid.uuid4()
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(
        return_value={"event_type": "pull_request", "payload": _PR_PAYLOAD}
    )
    pool.execute = AsyncMock()

    db_cfg = {"provider": "ollama", "model": "llama3", "base_url": "http://localhost", "api_key": ""}

    with (
        patch("app.jobs._get_repo_installation", new=AsyncMock(return_value=None)),
        patch("app.jobs.load_llm_config_from_db", new=AsyncMock(return_value=db_cfg)),
        patch("app.jobs.build_provider", return_value=MagicMock()),
        patch("app.jobs._get_or_create_job", new=AsyncMock(return_value=job_id)),
        patch("app.jobs.run_pipeline", new=AsyncMock(return_value="rev-1")),
    ):
        ctx = {"db_pool": pool, "redis": AsyncMock(), "job_try": 1}
        await process_webhook(ctx, "del-db-cfg")

    pool.execute.assert_called_once()


@pytest.mark.asyncio
async def test_process_webhook_per_repo_llm_override():
    job_id = uuid.uuid4()
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(
        return_value={"event_type": "pull_request", "payload": _PR_PAYLOAD}
    )
    pool.execute = AsyncMock()
    built_providers = []

    def capture_build(provider, **kwargs):
        built_providers.append(provider)
        return MagicMock()

    with (
        patch("app.jobs._get_repo_installation", new=AsyncMock(return_value={
            "config_json": {"enabled": True, "provider": "openai", "model": "gpt-4o"}
        })),
        patch("app.jobs.load_llm_config_from_db", new=AsyncMock(return_value=None)),
        patch("app.jobs.load_env_llm_config", return_value={"provider": "ollama", "model": "m", "base_url": "", "api_key": ""}),
        patch("app.jobs.build_provider", side_effect=capture_build),
        patch("app.jobs._get_or_create_job", new=AsyncMock(return_value=job_id)),
        patch("app.jobs.run_pipeline", new=AsyncMock(return_value="rev-1")),
    ):
        ctx = {"db_pool": pool, "redis": AsyncMock(), "job_try": 1}
        await process_webhook(ctx, "del-override")

    assert "openai" in built_providers


# ---------------------------------------------------------------------------
# post_feedback — uncovered branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_feedback_returns_when_review_not_found():
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=None)
    ctx = {"db_pool": pool, "job_try": 1}

    await post_feedback(ctx, str(uuid.uuid4()))

    pool.fetchval.assert_not_called()


@pytest.mark.asyncio
async def test_post_feedback_retries_on_rate_limit():
    pr_review_id = str(uuid.uuid4())
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value={
        "repo": "acme/backend",
        "pr_number": 1,
        "commit_sha": "sha",
        "feedback": {"comments": [], "summary": "ok", "generic_ratio": 0.0},
        "platform": "github",
        "github_review_id": None,
        "gitlab_discussion_id": None,
    })

    ctx = {"db_pool": pool, "job_try": 1}
    with patch("app.jobs.post_github_review", new=AsyncMock(side_effect=RateLimitError("rate limit"))):
        with pytest.raises(Retry):
            await post_feedback(ctx, pr_review_id)


@pytest.mark.asyncio
async def test_post_feedback_terminal_on_github_client_error():
    """GitHubClientError (4xx) must NOT retry — log and return."""
    pr_review_id = str(uuid.uuid4())
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value={
        "repo": "acme/backend",
        "pr_number": 1,
        "commit_sha": "sha",
        "feedback": {"comments": [], "summary": "ok", "generic_ratio": 0.0},
        "platform": "github",
        "github_review_id": None,
        "gitlab_discussion_id": None,
    })

    ctx = {"db_pool": pool, "job_try": 1}
    with patch("app.jobs.post_github_review", new=AsyncMock(side_effect=GitHubClientError("403 Forbidden"))):
        await post_feedback(ctx, pr_review_id)  # must not raise

    pool.fetchval.assert_not_called()


@pytest.mark.asyncio
async def test_post_feedback_retries_on_generic_exception():
    pr_review_id = str(uuid.uuid4())
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value={
        "repo": "acme/backend",
        "pr_number": 1,
        "commit_sha": "sha",
        "feedback": {"comments": [], "summary": "ok", "generic_ratio": 0.0},
        "platform": "github",
        "github_review_id": None,
        "gitlab_discussion_id": None,
    })

    ctx = {"db_pool": pool, "job_try": 1}
    with patch("app.jobs.post_github_review", new=AsyncMock(side_effect=Exception("unknown error"))):
        with pytest.raises(Retry):
            await post_feedback(ctx, pr_review_id)


@pytest.mark.asyncio
async def test_post_feedback_exhausts_retries_raises():
    pr_review_id = str(uuid.uuid4())
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value={
        "repo": "acme/backend",
        "pr_number": 1,
        "commit_sha": "sha",
        "feedback": {"comments": [], "summary": "ok", "generic_ratio": 0.0},
        "platform": "github",
        "github_review_id": None,
        "gitlab_discussion_id": None,
    })

    ctx = {"db_pool": pool, "job_try": 3}
    with patch("app.jobs.post_github_review", new=AsyncMock(side_effect=Exception("still failing"))):
        with pytest.raises(Exception, match="still failing"):
            await post_feedback(ctx, pr_review_id)
