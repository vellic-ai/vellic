"""Unit tests for GET /admin/stats."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.stats_router import router

_app = FastAPI()
_app.include_router(router)


def _make_pool(fetchrow_result, fetch_result=None):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    pool = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=_app), base_url="http://test")


_EMPTY_ROW = {
    "prs_reviewed_24h": 0,
    "prs_reviewed_7d": 0,
    "latency_p50_ms": 0,
    "latency_p95_ms": 0,
    "failure_rate_pct": Decimal("0.0"),
    "llm_provider": None,
    "llm_model": None,
}

_FULL_ROW = {
    "prs_reviewed_24h": 12,
    "prs_reviewed_7d": 84,
    "latency_p50_ms": 2340,
    "latency_p95_ms": 8100,
    "failure_rate_pct": Decimal("2.40"),
    "llm_provider": "ollama",
    "llm_model": "llama3.1:8b",
}

_TS = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)


async def test_empty_db_returns_zeros(client):
    pool = _make_pool(_EMPTY_ROW)
    with patch("app.stats_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["prs_reviewed_24h"] == 0
    assert data["prs_reviewed_7d"] == 0
    assert data["latency_p50_ms"] == 0
    assert data["latency_p95_ms"] == 0
    assert data["failure_rate_pct"] == 0.0
    assert data["llm_provider"] is None
    assert data["llm_model"] is None
    assert data["recent_deliveries"] == []


async def test_full_stats(client):
    delivery = MagicMock()
    delivery.__getitem__ = lambda self, k: {
        "delivery_id": "abc123",
        "event_type": "pull_request",
        "repo": "acme/backend",
        "received_at": _TS,
        "status": "done",
    }[k]

    pool = _make_pool(_FULL_ROW, [delivery])
    with patch("app.stats_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["prs_reviewed_24h"] == 12
    assert data["prs_reviewed_7d"] == 84
    assert data["latency_p50_ms"] == 2340
    assert data["latency_p95_ms"] == 8100
    assert data["failure_rate_pct"] == 2.4
    assert data["llm_provider"] == "ollama"
    assert data["llm_model"] == "llama3.1:8b"
    assert len(data["recent_deliveries"]) == 1
    d = data["recent_deliveries"][0]
    assert d["delivery_id"] == "abc123"
    assert d["repo"] == "acme/backend"
    assert d["status"] == "done"


async def test_recent_deliveries_capped_at_five(client):
    """SQL has LIMIT 5, verify we pass through whatever the DB returns."""
    deliveries = []
    for i in range(5):
        m = MagicMock()
        m.__getitem__ = lambda self, k, i=i: {
            "delivery_id": f"id-{i}",
            "event_type": "pull_request",
            "repo": "acme/repo",
            "received_at": _TS,
            "status": "done",
        }[k]
        deliveries.append(m)

    pool = _make_pool(_FULL_ROW, deliveries)
    with patch("app.stats_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/stats")
    assert r.status_code == 200
    assert len(r.json()["recent_deliveries"]) == 5


async def test_none_fields_coerced_to_zero(client):
    """None from DB (no rows matching) must not cause 500."""
    row = {**_EMPTY_ROW, "latency_p50_ms": None, "latency_p95_ms": None, "failure_rate_pct": None}
    pool = _make_pool(row)
    with patch("app.stats_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["latency_p50_ms"] == 0
    assert data["latency_p95_ms"] == 0
    assert data["failure_rate_pct"] == 0.0
