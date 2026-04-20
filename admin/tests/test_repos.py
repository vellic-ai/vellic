"""Unit tests for /admin/settings/repos endpoints and worker guard."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.repos_router import router

_app = FastAPI()
_app.include_router(router)

_TS = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
_REPO_ID = str(uuid.uuid4())


def _make_pool(fetch_result=None, fetchrow_result=None, execute_result="DELETE 1"):
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.execute = AsyncMock(return_value=execute_result)
    pool = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool, conn


def _make_row(**overrides):
    defaults = {
        "id": uuid.UUID(_REPO_ID),
        "platform": "github",
        "org": "acme",
        "repo": "backend",
        "config_json": {"enabled": True, "provider": "ollama", "model": "qwen2.5-coder:14b"},
        "created_at": _TS,
    }
    merged = {**defaults, **overrides}
    row = MagicMock()
    row.__getitem__ = lambda self, k: merged[k]
    row.keys = lambda: merged.keys()
    # Make dict(row) work
    row.__iter__ = lambda self: iter(merged)
    return row


def _as_dict(row_mock):
    """Build a plain dict from the mock row (mirrors dict(asyncpg.Record))."""
    return {k: row_mock[k] for k in ["id", "platform", "org", "repo", "config_json", "created_at"]}


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=_app), base_url="http://test")


# ---------------------------------------------------------------------------
# GET /admin/settings/repos
# ---------------------------------------------------------------------------

async def test_list_repos_empty(client):
    pool, _ = _make_pool(fetch_result=[])
    with patch("app.repos_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/settings/repos")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["items"] == []


async def test_list_repos_returns_items(client):
    row = _make_row()

    class FakeRecord(dict):
        pass

    fake = FakeRecord(_as_dict(row))
    pool, _ = _make_pool(fetch_result=[fake])
    with patch("app.repos_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/settings/repos")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["org"] == "acme"
    assert items[0]["repo"] == "backend"
    assert items[0]["platform"] == "github"
    assert items[0]["enabled"] is True


# ---------------------------------------------------------------------------
# POST /admin/settings/repos
# ---------------------------------------------------------------------------

async def test_create_repo_success(client):
    row = _make_row()

    class FakeRecord(dict):
        pass

    fake = FakeRecord(_as_dict(row))
    pool, conn = _make_pool(fetchrow_result=fake)
    conn.fetchrow = AsyncMock(side_effect=[None, fake])  # no duplicate, then INSERT result
    with patch("app.repos_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                "/admin/settings/repos",
                json={"platform": "github", "org": "acme", "repo": "backend"},
            )
    assert r.status_code == 201
    data = r.json()
    assert data["org"] == "acme"
    assert data["repo"] == "backend"


async def test_create_repo_duplicate_returns_409(client):
    row = _make_row()

    class FakeRecord(dict):
        pass

    fake = FakeRecord(_as_dict(row))
    pool, conn = _make_pool()
    conn.fetchrow = AsyncMock(return_value=fake)  # duplicate found
    with patch("app.repos_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                "/admin/settings/repos",
                json={"platform": "github", "org": "acme", "repo": "backend"},
            )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# POST /admin/settings/repos/{id}/toggle
# ---------------------------------------------------------------------------

async def test_toggle_repo_flips_enabled(client):
    row_disabled = _make_row(config_json={"enabled": False, "provider": "ollama", "model": "q"})

    class FakeRecord(dict):
        pass

    fake_initial = FakeRecord(_as_dict(row_disabled))
    row_enabled = _make_row(config_json={"enabled": True, "provider": "ollama", "model": "q"})
    fake_updated = FakeRecord(_as_dict(row_enabled))

    pool, conn = _make_pool()
    conn.fetchrow = AsyncMock(side_effect=[fake_initial, fake_updated])
    with patch("app.repos_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(f"/admin/settings/repos/{_REPO_ID}/toggle")
    assert r.status_code == 200
    assert r.json()["enabled"] is True


async def test_toggle_repo_not_found_returns_404(client):
    pool, conn = _make_pool()
    conn.fetchrow = AsyncMock(return_value=None)
    with patch("app.repos_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(f"/admin/settings/repos/{_REPO_ID}/toggle")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /admin/settings/repos/{id}
# ---------------------------------------------------------------------------

async def test_delete_repo_success(client):
    pool, conn = _make_pool(execute_result="DELETE 1")
    with patch("app.repos_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.delete(f"/admin/settings/repos/{_REPO_ID}")
    assert r.status_code == 204


async def test_delete_repo_not_found_returns_404(client):
    pool, conn = _make_pool(execute_result="DELETE 0")
    with patch("app.repos_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.delete(f"/admin/settings/repos/{_REPO_ID}")
    assert r.status_code == 404


