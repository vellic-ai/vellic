"""Unit tests for admin DLQ endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.dlq_router import router

_app = FastAPI()
_app.include_router(router)

_NOW = datetime(2026, 4, 21, 10, 0, 0, tzinfo=UTC)
_DLQ_ID = str(uuid.uuid4())
_DELIVERY_ID = "github-delivery-abc"


def _make_pool(fetch_result=None, fetchrow_result=None):
    rows = fetch_result or []
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=rows)
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.execute = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire.return_value = ctx
    return pool


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=_app), base_url="http://test")


def _dlq_row(**overrides):
    data = {
        "id": _DLQ_ID,
        "delivery_id": _DELIVERY_ID,
        "job_id": str(uuid.uuid4()),
        "last_error": "RuntimeError: pipeline exploded",
        "retry_count": 3,
        "status": "pending",
        "created_at": _NOW,
        "last_attempted_at": _NOW,
        "repo": "acme/backend",
        "pr_number": "42",
        "total_count": 1,
    }
    data.update(overrides)
    mock = MagicMock()
    mock.__getitem__ = lambda s, k: data[k]
    return mock


# ---------------------------------------------------------------------------
# GET /admin/dlq
# ---------------------------------------------------------------------------


async def test_list_dlq_empty(client):
    pool = _make_pool()
    with patch("app.dlq_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/dlq")
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_dlq_returns_items(client):
    row = _dlq_row()
    pool = _make_pool(fetch_result=[row])
    with patch("app.dlq_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/dlq?status=pending&limit=10&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["delivery_id"] == _DELIVERY_ID
    assert item["retry_count"] == 3
    assert item["status"] == "pending"
    assert item["repo"] == "acme/backend"


# ---------------------------------------------------------------------------
# POST /admin/dlq/{id}/replay
# ---------------------------------------------------------------------------


async def test_replay_dlq_entry_queues_job(client):
    fetchrow = {"id": _DLQ_ID, "delivery_id": _DELIVERY_ID, "status": "pending"}
    pool = _make_pool(fetchrow_result=fetchrow)
    mock_arq = AsyncMock()
    with (
        patch("app.dlq_router.db.get_pool", return_value=pool),
        patch("app.dlq_router.arq_pool.get_pool", return_value=mock_arq),
    ):
        async with client as c:
            r = await c.post(f"/admin/dlq/{_DLQ_ID}/replay")
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "queued"
    assert data["delivery_id"] == _DELIVERY_ID
    mock_arq.enqueue_job.assert_called_once_with("process_webhook", _DELIVERY_ID)


async def test_replay_dlq_entry_not_found(client):
    pool = _make_pool(fetchrow_result=None)
    with patch("app.dlq_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(f"/admin/dlq/{_DLQ_ID}/replay")
    assert r.status_code == 404


async def test_replay_discarded_entry_returns_409(client):
    fetchrow = {"id": _DLQ_ID, "delivery_id": _DELIVERY_ID, "status": "discarded"}
    pool = _make_pool(fetchrow_result=fetchrow)
    with patch("app.dlq_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(f"/admin/dlq/{_DLQ_ID}/replay")
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# DELETE /admin/dlq/{id}
# ---------------------------------------------------------------------------


async def test_discard_dlq_entry(client):
    fetchrow = {"id": _DLQ_ID, "delivery_id": _DELIVERY_ID, "status": "pending"}
    pool = _make_pool(fetchrow_result=fetchrow)
    with patch("app.dlq_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.delete(f"/admin/dlq/{_DLQ_ID}")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "discarded"
    assert data["dlq_id"] == _DLQ_ID


async def test_discard_already_discarded_returns_409(client):
    fetchrow = {"id": _DLQ_ID, "delivery_id": _DELIVERY_ID, "status": "discarded"}
    pool = _make_pool(fetchrow_result=fetchrow)
    with patch("app.dlq_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.delete(f"/admin/dlq/{_DLQ_ID}")
    assert r.status_code == 409


async def test_discard_not_found_returns_404(client):
    pool = _make_pool(fetchrow_result=None)
    with patch("app.dlq_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.delete(f"/admin/dlq/{_DLQ_ID}")
    assert r.status_code == 404
