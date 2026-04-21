"""Tests for pipeline runner — run_pipeline end-to-end (all external calls mocked)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.events import PREvent
from app.pipeline.models import AnalysisResult, DiffChunk, PRContext
from app.pipeline.runner import _flag_enabled, _merge_rule_violations, run_pipeline
from app.rules.models import RepoConfig, Rule, RuleViolation

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

_CTX = PRContext("acme/backend", 5, "head", "feat: thing", "does stuff", "main")
_CHUNKS = [DiffChunk("app.py", ["+foo = 1"])]
_RESULT = AnalysisResult(comments=[], summary="LGTM.", generic_ratio=0.0)
_EMPTY_CONFIG = RepoConfig(repo_id="acme/backend")


def _make_pool():
    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=mock_conn)
    pool.fetchrow = AsyncMock(return_value=None)
    pool.execute = AsyncMock()
    return pool


# ---------------------------------------------------------------------------
# _flag_enabled
# ---------------------------------------------------------------------------

def test_flag_enabled_known_flag_returns_default():
    assert isinstance(_flag_enabled("pipeline.diff"), bool)


def test_flag_enabled_unknown_flag_returns_false():
    assert _flag_enabled("unknown.flag.xyz") is False


# ---------------------------------------------------------------------------
# _merge_rule_violations
# ---------------------------------------------------------------------------

def test_merge_rule_violations_empty():
    result = _merge_rule_violations(_RESULT, [])
    assert result is _RESULT


def test_merge_rule_violations_appends_comments():
    violations = [RuleViolation("no-print", "app.py", 5, "print(x)", "warning", "No print")]
    merged = _merge_rule_violations(_RESULT, violations)
    assert len(merged.comments) == 1
    assert merged.comments[0].confidence == 1.0
    assert "no-print" in merged.comments[0].rationale


# ---------------------------------------------------------------------------
# run_pipeline — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_pipeline_returns_pr_review_id():
    pool = _make_pool()
    arq_redis = AsyncMock()
    llm = MagicMock()
    job_id = uuid.uuid4()
    expected_id = str(uuid.uuid4())

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX),
        patch("app.pipeline.runner._flag_enabled", return_value=True),
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=_CHUNKS)),
        patch("app.pipeline.runner._ast_enricher") as mock_enricher,
        patch("app.pipeline.runner.load_repo_config", new=AsyncMock(return_value=_EMPTY_CONFIG)),
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=_RESULT)),
        patch("app.pipeline.runner.persist", new=AsyncMock(return_value=expected_id)),
    ):
        mock_enricher.enrich_all.return_value = {}
        returned = await run_pipeline(_EVENT, pool, llm, job_id, arq_redis)

    assert returned == expected_id


@pytest.mark.asyncio
async def test_run_pipeline_passes_correct_args_to_stages():
    pool = _make_pool()
    arq_redis = AsyncMock()
    llm = MagicMock()
    job_id = uuid.uuid4()

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX) as mock_gather,
        patch("app.pipeline.runner._flag_enabled", return_value=True),
        patch(
            "app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=_CHUNKS)
        ) as mock_fetch,
        patch("app.pipeline.runner._ast_enricher") as mock_enricher,
        patch("app.pipeline.runner.load_repo_config", new=AsyncMock(return_value=_EMPTY_CONFIG)),
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=_RESULT)) as mock_analyze,
        patch("app.pipeline.runner.persist", new=AsyncMock(return_value="rev-id")) as mock_persist,
    ):
        mock_enricher.enrich_all.return_value = {}
        await run_pipeline(_EVENT, pool, llm, job_id, arq_redis)

    mock_gather.assert_called_once_with(_EVENT)
    mock_fetch.assert_called_once_with(_EVENT.diff_url)
    mock_analyze.assert_called_once_with(_CTX, _CHUNKS, llm, custom_instructions=None)
    mock_persist.assert_called_once_with(pool, _CTX, _RESULT, job_id, arq_redis)


@pytest.mark.asyncio
async def test_run_pipeline_with_rule_violations_merges_comments():
    pool = _make_pool()
    violation = RuleViolation("no-todo", "app.py", 3, "TODO: fix", "warning", "No TODOs")
    config_with_rules = RepoConfig(
        repo_id="acme/backend",
        rules=[Rule("no-todo", r"TODO:", "No TODOs")],
    )

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX),
        patch("app.pipeline.runner._flag_enabled", return_value=True),
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=_CHUNKS)),
        patch("app.pipeline.runner._ast_enricher") as mock_enricher,
        patch(
            "app.pipeline.runner.load_repo_config",
            new=AsyncMock(return_value=config_with_rules),
        ),
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=_RESULT)),
        patch("app.pipeline.runner.evaluate_rules", return_value=[violation]),
        patch("app.pipeline.runner.persist", new=AsyncMock(return_value="rv-1")) as mock_persist,
    ):
        mock_enricher.enrich_all.return_value = {}
        await run_pipeline(_EVENT, pool, MagicMock(), uuid.uuid4(), AsyncMock())

    # persist receives the merged result
    merged_result = mock_persist.call_args[0][2]
    assert len(merged_result.comments) == 1


@pytest.mark.asyncio
async def test_run_pipeline_propagates_fetch_error():
    pool = _make_pool()

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX),
        patch("app.pipeline.runner._flag_enabled", return_value=True),
        patch(
            "app.pipeline.runner.fetch_diff_chunks",
            new=AsyncMock(side_effect=RuntimeError("net error")),
        ),
    ):
        with pytest.raises(RuntimeError, match="net error"):
            await run_pipeline(_EVENT, pool, MagicMock(), uuid.uuid4(), AsyncMock())


@pytest.mark.asyncio
async def test_run_pipeline_returns_empty_when_diff_flag_disabled():
    pool = _make_pool()

    def flag_side(key: str) -> bool:
        return key != "pipeline.diff"

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX),
        patch("app.pipeline.runner._flag_enabled", side_effect=flag_side),
    ):
        result = await run_pipeline(_EVENT, pool, MagicMock(), uuid.uuid4(), AsyncMock())

    assert result == ""


# ---------------------------------------------------------------------------
# Stage 2d: platform.prompt_dsl flag integration (VEL-116)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_pipeline_dsl_flag_disabled_passes_no_custom_instructions():
    """When platform.prompt_dsl is off, analyze receives custom_instructions=None."""
    pool = _make_pool()

    def flag_side(key: str) -> bool:
        return key != "platform.prompt_dsl"

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX),
        patch("app.pipeline.runner._flag_enabled", side_effect=flag_side),
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=_CHUNKS)),
        patch("app.pipeline.runner._ast_enricher") as mock_enricher,
        patch("app.pipeline.runner.load_repo_config", new=AsyncMock(return_value=_EMPTY_CONFIG)),
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=_RESULT)) as mock_analyze,
        patch("app.pipeline.runner.persist", new=AsyncMock(return_value="rv-1")),
    ):
        mock_enricher.enrich_all.return_value = {}
        await run_pipeline(_EVENT, pool, MagicMock(), uuid.uuid4(), AsyncMock())

    mock_analyze.assert_called_once()
    _, _, _, kwargs = (*mock_analyze.call_args.args, mock_analyze.call_args.kwargs)
    assert kwargs.get("custom_instructions") is None


@pytest.mark.asyncio
async def test_run_pipeline_dsl_flag_enabled_with_prompts_passes_custom_instructions():
    """When platform.prompt_dsl is on and prompts are found, analyze gets the rendered body."""
    pool = _make_pool()
    _RENDERED_BODY = "Custom DSL instructions for this repo."

    from app.prompts.models import ResolvedPrompt

    def flag_side(key: str) -> bool:
        return True  # all flags on

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX),
        patch("app.pipeline.runner._flag_enabled", side_effect=flag_side),
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=_CHUNKS)),
        patch("app.pipeline.runner._ast_enricher") as mock_enricher,
        patch("app.pipeline.runner.load_repo_config", new=AsyncMock(return_value=_EMPTY_CONFIG)),
        patch(
            "app.pipeline.runner.load_repo_prompts",
            new=AsyncMock(return_value=[object()]),  # non-empty list signals prompts exist
        ),
        patch("app.pipeline.runner.resolve_all", return_value=[]),
        patch("app.pipeline.runner.cascade_merge", return_value=[]),
        patch(
            "app.pipeline.runner.build_resolved_prompt",
            return_value=ResolvedPrompt(body=_RENDERED_BODY, sources=["preset"]),
        ),
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=_RESULT)) as mock_analyze,
        patch("app.pipeline.runner.persist", new=AsyncMock(return_value="rv-2")),
    ):
        mock_enricher.enrich_all.return_value = {}
        await run_pipeline(_EVENT, pool, MagicMock(), uuid.uuid4(), AsyncMock())

    mock_analyze.assert_called_once()
    assert mock_analyze.call_args.kwargs.get("custom_instructions") == _RENDERED_BODY


@pytest.mark.asyncio
async def test_run_pipeline_dsl_flag_enabled_no_prompts_uses_default_instructions():
    """When flag is on but no prompts are found, custom_instructions stays None."""
    pool = _make_pool()

    with (
        patch("app.pipeline.runner.gather_context", return_value=_CTX),
        patch("app.pipeline.runner._flag_enabled", return_value=True),
        patch("app.pipeline.runner.fetch_diff_chunks", new=AsyncMock(return_value=_CHUNKS)),
        patch("app.pipeline.runner._ast_enricher") as mock_enricher,
        patch("app.pipeline.runner.load_repo_config", new=AsyncMock(return_value=_EMPTY_CONFIG)),
        patch("app.pipeline.runner.load_repo_prompts", new=AsyncMock(return_value=[])),
        patch("app.pipeline.runner.analyze", new=AsyncMock(return_value=_RESULT)) as mock_analyze,
        patch("app.pipeline.runner.persist", new=AsyncMock(return_value="rv-3")),
    ):
        mock_enricher.enrich_all.return_value = {}
        await run_pipeline(_EVENT, pool, MagicMock(), uuid.uuid4(), AsyncMock())

    mock_analyze.assert_called_once()
    assert mock_analyze.call_args.kwargs.get("custom_instructions") is None
