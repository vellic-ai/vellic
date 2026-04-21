"""Tests for pipeline runner — run_pipeline end-to-end (all external calls mocked)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.events import PREvent
from app.pipeline.models import AnalysisResult, DiffChunk, PRContext
from app.pipeline.runner import run_pipeline
from app.rules.models import RepoConfig

_EVENT = PREvent(
    platform="github",
    event_type="pull_request",
    delivery_id="d-1",
    repo="acme/backend",
    pr_number=5,
    action="opened",
    diff_url="https://api.github.com/repos/acme/backend/pulls/5/files",
    base_sha="base",
    head_sha="head",
    base_branch="main",
    title="feat: thing",
    description="does stuff",
)


@pytest.mark.asyncio
async def test_run_pipeline_returns_pr_review_id():
    pool = MagicMock()
    arq_redis = AsyncMock()
    llm = MagicMock()
    job_id = uuid.uuid4()
    expected_id = str(uuid.uuid4())

    chunks = [DiffChunk("app.py", ["+foo = 1"])]
    result = AnalysisResult(comments=[], summary="LGTM.", generic_ratio=0.0)

    with (
        patch("app.pipeline.runner.gather_context", return_value=PRContext("acme/backend", 5, "head", "feat: thing", "does stuff", "main")),
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=chunks)),
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=result)),
        patch("app.pipeline.runner.load_repo_config", new=AsyncMock(return_value=RepoConfig(repo_id="acme/backend"))),
        patch("app.pipeline.runner.persist", new=AsyncMock(return_value=expected_id)),
    ):
        returned = await run_pipeline(_EVENT, pool, llm, job_id, arq_redis)

    assert returned == expected_id


@pytest.mark.asyncio
async def test_run_pipeline_passes_correct_args_to_stages():
    pool = MagicMock()
    arq_redis = AsyncMock()
    llm = MagicMock()
    job_id = uuid.uuid4()
    ctx = PRContext("acme/backend", 5, "head", "feat: thing", "does stuff", "main")
    chunks = [DiffChunk("app.py", ["+x"])]
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)

    with (
        patch("app.pipeline.runner.gather_context", return_value=ctx) as mock_gather,
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=chunks)) as mock_fetch,
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=result)) as mock_analyze,
        patch("app.pipeline.runner.load_repo_config", new=AsyncMock(return_value=RepoConfig(repo_id="acme/backend"))),
        patch("app.pipeline.runner.persist", new=AsyncMock(return_value="rev-id")) as mock_persist,
    ):
        await run_pipeline(_EVENT, pool, llm, job_id, arq_redis)

    mock_gather.assert_called_once_with(_EVENT)
    mock_fetch.assert_called_once_with(_EVENT.diff_url)
    mock_analyze.assert_called_once_with(ctx, chunks, llm)
    mock_persist.assert_called_once_with(pool, ctx, result, job_id, arq_redis)


@pytest.mark.asyncio
async def test_run_pipeline_propagates_fetch_error():
    pool = MagicMock()
    llm = MagicMock()
    job_id = uuid.uuid4()
    ctx = PRContext("acme/backend", 5, "head", "t", "", "main")

    with (
        patch("app.pipeline.runner.gather_context", return_value=ctx),
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(side_effect=RuntimeError("network error"))),
        patch("app.pipeline.runner.load_repo_config", new=AsyncMock(return_value=RepoConfig(repo_id="acme/backend"))),
    ):
        with pytest.raises(RuntimeError, match="network error"):
            await run_pipeline(_EVENT, pool, llm, job_id, AsyncMock())
