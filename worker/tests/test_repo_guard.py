"""Unit tests for repo allow-list worker guard (_get_repo_installation)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.jobs import _get_repo_installation


async def test_returns_specific_row():
    specific = {"config_json": {"enabled": True, "provider": "ollama", "model": "q"}}
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=[specific])
    result = await _get_repo_installation(pool, "github", "acme", "backend")
    assert result == specific


async def test_returns_none_when_no_rows():
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=[])
    result = await _get_repo_installation(pool, "github", "acme", "backend")
    assert result is None


async def test_disabled_flag_in_config_json():
    """Guard caller checks config_json.enabled; confirm disabled row is returned as-is."""
    disabled = {"config_json": {"enabled": False, "provider": "ollama", "model": "q"}}
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=[disabled])
    inst = await _get_repo_installation(pool, "github", "acme", "backend")
    assert inst is not None
    assert inst["config_json"].get("enabled", True) is False
