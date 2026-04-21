"""Unit tests for /admin/repos/{repo_id}/mcp endpoints."""

import json
import os
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("LLM_ENCRYPTION_KEY", "ZmFrZWtleWZha2VrZXlmYWtla2V5ZmFrZWtleWZhaz0=")

from app.mcp_router import router  # noqa: E402

_app = FastAPI()
_app.include_router(router)

_TS = datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC)
_REPO_ID = str(uuid.uuid4())
_SERVER_ID = str(uuid.uuid4())


def _make_pool(fetchrow=None, fetch=None, execute="DELETE 1"):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow)
    conn.fetch = AsyncMock(return_value=fetch or [])
    conn.execute = AsyncMock(return_value=execute)
    pool = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool, conn


def _make_inst_row():
    return {"id": uuid.UUID(_REPO_ID)}


def _make_server_row(**overrides):
    defaults = {
        "id": uuid.UUID(_SERVER_ID),
        "installation_id": uuid.UUID(_REPO_ID),
        "name": "context7",
        "url": "npx -y @upstash/context7-mcp@latest",
        "credentials_enc": None,
        "enabled": True,
        "created_at": _TS,
    }
    return {**defaults, **overrides}


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=_app), base_url="http://test")


# ------------------------------------------------------------------
# GET /admin/repos/{repo_id}/mcp
# ------------------------------------------------------------------

async def test_list_mcp_empty(client):
    pool, conn = _make_pool(fetchrow=_make_inst_row(), fetch=[])
    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get(f"/admin/repos/{_REPO_ID}/mcp")
    assert r.status_code == 200
    assert r.json()["items"] == []


async def test_list_mcp_repo_not_found(client):
    pool, conn = _make_pool(fetchrow=None)
    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get(f"/admin/repos/{_REPO_ID}/mcp")
    assert r.status_code == 404


async def test_list_mcp_returns_items(client):
    record = _make_server_row()
    pool, conn = _make_pool(fetchrow=_make_inst_row(), fetch=[record])
    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get(f"/admin/repos/{_REPO_ID}/mcp")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "context7"
    assert items[0]["credentials_set"] is False


# ------------------------------------------------------------------
# POST /admin/repos/{repo_id}/mcp
# ------------------------------------------------------------------

async def test_attach_mcp_server(client):
    server_row = _make_server_row()
    pool, conn = _make_pool()
    conn.fetchrow = AsyncMock(side_effect=[_make_inst_row(), None, server_row])

    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                f"/admin/repos/{_REPO_ID}/mcp",
                json={"name": "context7", "url": "npx -y @upstash/context7-mcp@latest"},
            )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "context7"
    assert data["credentials_set"] is False


async def test_attach_mcp_server_with_credentials(client):
    server_row = _make_server_row(credentials_enc="encrypted")
    pool, conn = _make_pool()
    conn.fetchrow = AsyncMock(side_effect=[_make_inst_row(), None, server_row])

    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                f"/admin/repos/{_REPO_ID}/mcp",
                json={
                    "name": "context7",
                    "url": "npx ...",
                    "credentials": {"token": "secret123"},
                },
            )
    assert r.status_code == 201
    assert r.json()["credentials_set"] is True


async def test_attach_mcp_repo_not_found(client):
    pool, conn = _make_pool(fetchrow=None)
    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                f"/admin/repos/{_REPO_ID}/mcp",
                json={"name": "ctx", "url": "npx ..."},
            )
    assert r.status_code == 404


async def test_attach_mcp_conflict(client):
    existing = _make_server_row()
    pool, conn = _make_pool()
    conn.fetchrow = AsyncMock(side_effect=[_make_inst_row(), existing])

    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                f"/admin/repos/{_REPO_ID}/mcp",
                json={"name": "context7", "url": "npx ..."},
            )
    assert r.status_code == 409


async def test_attach_mcp_missing_name(client):
    pool, _ = _make_pool()
    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                f"/admin/repos/{_REPO_ID}/mcp",
                json={"name": "", "url": "npx ..."},
            )
    assert r.status_code == 422


# ------------------------------------------------------------------
# DELETE /admin/repos/{repo_id}/mcp/{server_id}
# ------------------------------------------------------------------

async def test_detach_mcp_server(client):
    pool, conn = _make_pool(execute="DELETE 1")
    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.delete(f"/admin/repos/{_REPO_ID}/mcp/{_SERVER_ID}")
    assert r.status_code == 204


async def test_detach_mcp_not_found(client):
    pool, conn = _make_pool(execute="DELETE 0")
    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.delete(f"/admin/repos/{_REPO_ID}/mcp/{_SERVER_ID}")
    assert r.status_code == 404


# ------------------------------------------------------------------
# PATCH /admin/repos/{repo_id}/mcp/{server_id}
# ------------------------------------------------------------------

async def test_patch_mcp_server_disable(client):
    existing = _make_server_row(enabled=True)
    updated = _make_server_row(enabled=False)
    pool, conn = _make_pool()
    conn.fetchrow = AsyncMock(side_effect=[existing, updated])

    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.patch(
                f"/admin/repos/{_REPO_ID}/mcp/{_SERVER_ID}",
                json={"enabled": False},
            )
    assert r.status_code == 200
    assert r.json()["enabled"] is False


async def test_patch_mcp_server_not_found(client):
    pool, conn = _make_pool(fetchrow=None)
    with patch("app.mcp_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.patch(
                f"/admin/repos/{_REPO_ID}/mcp/{_SERVER_ID}",
                json={"enabled": False},
            )
    assert r.status_code == 404
