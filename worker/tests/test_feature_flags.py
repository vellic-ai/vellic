"""Tests for feature flag guards wired into the pipeline and LLM registry."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.registry import build_provider, register
from app.pipeline.runner import _flag_enabled


# ---------------------------------------------------------------------------
# _flag_enabled helper
# ---------------------------------------------------------------------------


def test_flag_enabled_known_default_true():
    assert _flag_enabled("pipeline.diff") is True


def test_flag_enabled_known_default_false():
    assert _flag_enabled("pipeline.security_scan") is False


def test_flag_enabled_unknown_returns_false():
    assert _flag_enabled("no.such.flag") is False


def test_flag_enabled_env_override_true(monkeypatch):
    monkeypatch.setenv("VELLIC_FEATURE_PIPELINE_SECURITY_SCAN", "true")
    assert _flag_enabled("pipeline.security_scan") is True


def test_flag_enabled_env_override_false(monkeypatch):
    monkeypatch.setenv("VELLIC_FEATURE_PIPELINE_DIFF", "false")
    assert _flag_enabled("pipeline.diff") is False


# ---------------------------------------------------------------------------
# build_provider — flag guard
# ---------------------------------------------------------------------------


def test_build_provider_disabled_flag_raises(monkeypatch):
    monkeypatch.setenv("VELLIC_FEATURE_LLM_OPENAI", "false")
    with pytest.raises(ValueError, match="disabled by feature flag"):
        build_provider("openai")


def test_build_provider_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_provider("nonexistent_provider")


def test_build_provider_unknown_flag_defaults_enabled():
    """Providers not in _PROVIDER_FLAGS are not blocked even if no flag exists."""
    _dummy_cls = MagicMock(return_value=object())
    with patch("app.llm.registry._REGISTRY", {"custom": _dummy_cls}):
        result = build_provider("custom")
    _dummy_cls.assert_called_once()


# ---------------------------------------------------------------------------
# run_pipeline — diff flag gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_pipeline_skips_when_diff_disabled(monkeypatch):
    monkeypatch.setenv("VELLIC_FEATURE_PIPELINE_DIFF", "false")

    from app.pipeline.runner import run_pipeline
    from app.events import PREvent

    event = PREvent(
        platform="github",
        event_type="pull_request",
        delivery_id="d1",
        repo="acme/backend",
        pr_number=1,
        action="opened",
        diff_url="https://example.com/diff",
        base_sha="base",
        head_sha="head",
        base_branch="main",
        title="t",
        description="",
    )
    pool = MagicMock()
    llm = MagicMock()
    arq = MagicMock()

    result = await run_pipeline(event, pool, llm, uuid.uuid4(), arq)
    assert result == ""


@pytest.mark.asyncio
async def test_run_pipeline_skips_when_llm_analysis_disabled(monkeypatch):
    monkeypatch.setenv("VELLIC_FEATURE_PIPELINE_LLM_ANALYSIS", "false")

    from app.pipeline.runner import run_pipeline
    from app.events import PREvent
    from app.pipeline.models import DiffChunk

    event = PREvent(
        platform="github",
        event_type="pull_request",
        delivery_id="d2",
        repo="acme/backend",
        pr_number=2,
        action="opened",
        diff_url="https://example.com/diff",
        base_sha="base",
        head_sha="head",
        base_branch="main",
        title="t",
        description="",
    )
    pool = MagicMock()
    llm = MagicMock()
    arq = MagicMock()

    with patch("app.pipeline.runner.fetch_diff_chunks", AsyncMock(return_value=[DiffChunk("f.py", ["+x"])])):
        result = await run_pipeline(event, pool, llm, uuid.uuid4(), arq)

    assert result == ""
    llm.complete.assert_not_called()
