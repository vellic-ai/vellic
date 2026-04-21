"""Integration test: pipeline runner applies repo-specific rules."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.events import PREvent
from app.pipeline.models import AnalysisResult, DiffChunk, PRContext
from app.pipeline.runner import run_pipeline, _merge_rule_violations
from app.rules.models import RepoConfig, Rule, RuleViolation

_EVENT = PREvent(
    platform="github",
    event_type="pull_request",
    delivery_id="d-rules-1",
    repo="acme/backend",
    pr_number=7,
    action="opened",
    diff_url="https://api.github.com/repos/acme/backend/pulls/7/files",
    base_sha="base",
    head_sha="head",
    base_branch="main",
    title="feat: add feature",
    description="adds stuff",
)

_CTX = PRContext("acme/backend", 7, "head", "feat: add feature", "adds stuff", "main")
_CHUNKS = [DiffChunk("app.py", ["+print('debug')"])]


# ---------------------------------------------------------------------------
# _merge_rule_violations unit
# ---------------------------------------------------------------------------

def test_merge_rule_violations_empty():
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    merged = _merge_rule_violations(result, [])
    assert merged is result


def test_merge_rule_violations_appends_comments():
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    violations = [
        RuleViolation(
            rule_id="no_print",
            file="app.py",
            line=1,
            matched_text="print('debug')",
            severity="warning",
            description="No print statements",
        )
    ]
    merged = _merge_rule_violations(result, violations)
    assert len(merged.comments) == 1
    comment = merged.comments[0]
    assert comment.file == "app.py"
    assert comment.line == 1
    assert comment.confidence == 1.0
    assert "WARNING" in comment.body
    assert "No print statements" in comment.body
    assert "no_print" in comment.rationale


def test_merge_preserves_existing_llm_comments():
    from app.pipeline.models import ReviewComment
    existing = ReviewComment(file="x.py", line=2, body="fix this", confidence=0.8, rationale="r")
    result = AnalysisResult(comments=[existing], summary="ok", generic_ratio=0.0)
    violations = [
        RuleViolation(rule_id="r1", file="app.py", line=1, matched_text="x", severity="warning", description="d")
    ]
    merged = _merge_rule_violations(result, violations)
    assert len(merged.comments) == 2
    assert merged.comments[0] is existing


# ---------------------------------------------------------------------------
# run_pipeline with rules applied
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_pipeline_rules_violations_merged():
    """Custom rules for the repo produce extra comments in the final result."""
    pool = MagicMock()
    arq_redis = AsyncMock()
    llm = MagicMock()
    job_id = uuid.uuid4()
    expected_id = str(uuid.uuid4())

    llm_result = AnalysisResult(comments=[], summary="LGTM.", generic_ratio=0.0)
    repo_config = RepoConfig(
        repo_id="acme/backend",
        rules=[Rule(id="no_print", pattern=r"print\(", severity="warning")],
        ignore=[],
        severity_threshold="info",
    )

    captured_result: list[AnalysisResult] = []

    async def fake_persist(pool, ctx, result, job_id, arq_redis):
        captured_result.append(result)
        return expected_id

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX),
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=_CHUNKS)),
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=llm_result)),
        patch("app.pipeline.runner.load_repo_config", new=AsyncMock(return_value=repo_config)),
        patch("app.pipeline.runner.persist", new=fake_persist),
    ):
        returned = await run_pipeline(_EVENT, pool, llm, job_id, arq_redis)

    assert returned == expected_id
    assert len(captured_result) == 1
    final = captured_result[0]
    # Rule violation for print() in the added line should be present
    assert any("no_print" in c.rationale for c in final.comments)


@pytest.mark.asyncio
async def test_run_pipeline_no_rules_no_extra_comments():
    """Repo with no custom rules: result is unmodified from LLM analysis."""
    pool = MagicMock()
    arq_redis = AsyncMock()
    llm = MagicMock()
    job_id = uuid.uuid4()
    expected_id = str(uuid.uuid4())

    llm_result = AnalysisResult(comments=[], summary="LGTM.", generic_ratio=0.0)
    empty_config = RepoConfig(repo_id="acme/backend")

    captured_result: list[AnalysisResult] = []

    async def fake_persist(pool, ctx, result, job_id, arq_redis):
        captured_result.append(result)
        return expected_id

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX),
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=_CHUNKS)),
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=llm_result)),
        patch("app.pipeline.runner.load_repo_config", new=AsyncMock(return_value=empty_config)),
        patch("app.pipeline.runner.persist", new=fake_persist),
    ):
        await run_pipeline(_EVENT, pool, llm, job_id, arq_redis)

    assert captured_result[0].comments == []


@pytest.mark.asyncio
async def test_run_pipeline_rules_loader_called_with_repo():
    """load_repo_config is called with the correct repo identifier."""
    pool = MagicMock()
    arq_redis = AsyncMock()
    llm = MagicMock()
    job_id = uuid.uuid4()

    mock_load = AsyncMock(return_value=RepoConfig(repo_id="acme/backend"))

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX),
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=_CHUNKS)),
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=AnalysisResult())),
        patch("app.pipeline.runner.load_repo_config", new=mock_load),
        patch("app.pipeline.runner.persist", new=AsyncMock(return_value="id")),
    ):
        await run_pipeline(_EVENT, pool, llm, job_id, arq_redis)

    mock_load.assert_called_once_with(pool, "acme/backend")
