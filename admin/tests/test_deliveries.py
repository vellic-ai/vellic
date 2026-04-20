"""Tests for GET /admin/deliveries and POST /admin/replay/{delivery_id}."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.deliveries_router import router

_app = FastAPI()
_app.include_router(router)


def _make_pool(fetch_result=None, fetchrow_result=None):
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    pool = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool


_TS = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)


def _make_row(**kwargs):
    defaults = {
        "delivery_id": "dlv_abc123",
        "event_type": "pull_request.opened",
        "received_at": _TS,
        "processed_at": _TS,
        "status": "done",
        "job_id": "job-uuid-1",
        "total_count": 1,
    }
    merged = {**defaults, **kwargs}
    row = MagicMock()
    row.__getitem__ = lambda self, k: merged[k]
    return row


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=_app), base_url="http://test")


async def test_list_deliveries_empty(client):
    pool = _make_pool(fetch_result=[])
    with patch("app.deliveries_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/deliveries")
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 50
    assert data["offset"] == 0


async def test_list_deliveries_returns_items(client):
    row = _make_row()
    pool = _make_pool(fetch_result=[row])
    with patch("app.deliveries_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/deliveries")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["delivery_id"] == "dlv_abc123"
    assert item["event_type"] == "pull_request.opened"
    assert item["status"] == "done"
    assert item["job_id"] == "job-uuid-1"
    assert item["received_at"] is not None
    assert item["processed_at"] is not None


async def test_list_deliveries_pagination_params(client):
    pool = _make_pool(fetch_result=[])
    with patch("app.deliveries_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/deliveries?limit=10&offset=20")
    assert r.status_code == 200
    data = r.json()
    assert data["limit"] == 10
    assert data["offset"] == 20


async def test_list_deliveries_null_timestamps(client):
    row = _make_row(received_at=None, processed_at=None)
    pool = _make_pool(fetch_result=[row])
    with patch("app.deliveries_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/deliveries")
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["received_at"] is None
    assert item["processed_at"] is None


async def test_list_deliveries_pending_status(client):
    row = _make_row(status="pending", job_id=None)
    pool = _make_pool(fetch_result=[row])
    with patch("app.deliveries_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/deliveries")
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["status"] == "pending"
    assert item["job_id"] is None


async def test_replay_success(client):
    delivery_row = MagicMock()
    delivery_row.__getitem__ = lambda self, k: {
        "delivery_id": "dlv_abc123",
        "event_type": "pull_request.opened",
    }[k]
    pool = _make_pool(fetchrow_result=delivery_row)

    arq_mock = AsyncMock()
    arq_mock.enqueue_job = AsyncMock(return_value=None)

    with (
        patch("app.deliveries_router.db.get_pool", return_value=pool),
        patch("app.deliveries_router.arq_pool.get_pool", return_value=arq_mock),
    ):
        async with client as c:
            r = await c.post("/admin/replay/dlv_abc123")

    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "queued"
    assert data["delivery_id"] == "dlv_abc123"
    assert data["event_type"] == "pull_request.opened"
    arq_mock.enqueue_job.assert_awaited_once_with("process_webhook", "dlv_abc123")


async def test_replay_not_found(client):
    pool = _make_pool(fetchrow_result=None)

    with patch("app.deliveries_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post("/admin/replay/dlv_missing")

    assert r.status_code == 404
    assert "not found" in r.json()["detail"]
