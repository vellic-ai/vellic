"""Unit tests for worker/app/prompts/store.py CRUD helpers (VEL-115)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.prompts.store import delete_override, get_override, list_overrides, upsert_override


def _conn(*, fetch=None, fetchrow=None, execute=None) -> AsyncMock:
    conn = AsyncMock()
    if fetch is not None:
        conn.fetch = AsyncMock(return_value=fetch)
    if fetchrow is not None:
        conn.fetchrow = AsyncMock(return_value=fetchrow)
    if execute is not None:
        conn.execute = AsyncMock(return_value=execute)
    return conn


# ---------------------------------------------------------------------------
# list_overrides
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_overrides_returns_rows():
    rows = [
        {"path": "api-review", "body": "---\n---\nbody1", "updated_at": None},
        {"path": "security", "body": "---\n---\nbody2", "updated_at": None},
    ]
    conn = _conn(fetch=rows)
    result = await list_overrides(conn, "org/repo")
    assert len(result) == 2
    assert result[0]["path"] == "api-review"
    assert result[1]["path"] == "security"


@pytest.mark.asyncio
async def test_list_overrides_empty():
    conn = _conn(fetch=[])
    result = await list_overrides(conn, "org/repo")
    assert result == []


@pytest.mark.asyncio
async def test_list_overrides_passes_repo_id():
    conn = _conn(fetch=[])
    await list_overrides(conn, "myorg/myrepo")
    conn.fetch.assert_called_once()
    call_args = conn.fetch.call_args
    assert "myorg/myrepo" in call_args.args


# ---------------------------------------------------------------------------
# get_override
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_override_found():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    row = {"path": "api-review", "body": "---\n---\nbody", "updated_at": now}
    conn = _conn(fetchrow=row)
    result = await get_override(conn, "org/repo", "api-review")
    assert result is not None
    assert result["path"] == "api-review"
    assert result["updated_at"] == now


@pytest.mark.asyncio
async def test_get_override_not_found_returns_none():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    result = await get_override(conn, "org/repo", "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_override_passes_both_params():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    await get_override(conn, "org/repo", "my-prompt")
    call_args = conn.fetchrow.call_args
    assert "org/repo" in call_args.args
    assert "my-prompt" in call_args.args


# ---------------------------------------------------------------------------
# upsert_override
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_override_returns_updated_at():
    now = datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC)
    conn = _conn(fetchrow={"updated_at": now})
    result = await upsert_override(conn, "org/repo", "security", "---\n---\nbody")
    assert result == now


@pytest.mark.asyncio
async def test_upsert_override_passes_all_params():
    now = datetime(2026, 4, 21, tzinfo=UTC)
    conn = _conn(fetchrow={"updated_at": now})
    await upsert_override(conn, "acme/api", "review", "---\n---\ncontent")
    call_args = conn.fetchrow.call_args
    assert "acme/api" in call_args.args
    assert "review" in call_args.args
    assert "---\n---\ncontent" in call_args.args


# ---------------------------------------------------------------------------
# delete_override
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_override_returns_true_when_deleted():
    conn = _conn(execute="DELETE 1")
    result = await delete_override(conn, "org/repo", "api-review")
    assert result is True


@pytest.mark.asyncio
async def test_delete_override_returns_false_when_not_found():
    conn = _conn(execute="DELETE 0")
    result = await delete_override(conn, "org/repo", "nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_delete_override_passes_params():
    conn = _conn(execute="DELETE 1")
    await delete_override(conn, "acme/api", "old-review")
    call_args = conn.execute.call_args
    assert "acme/api" in call_args.args
    assert "old-review" in call_args.args
