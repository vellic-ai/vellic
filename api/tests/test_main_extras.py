"""Tests for api/app/main.py — health endpoint and lifespan helpers."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok():
    with (
        patch("app.webhook.get_db_pool", return_value=None),
        patch("app.webhook.get_arq_pool", return_value=None),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "api"


@pytest.mark.asyncio
async def test_lifespan_init_and_teardown():
    """Lifespan should call init/close on both pools in order."""
    from app.main import lifespan

    init_calls = []
    close_calls = []

    async def fake_db_init():
        init_calls.append("db")

    async def fake_arq_init():
        init_calls.append("arq")

    async def fake_arq_close():
        close_calls.append("arq")

    async def fake_db_close():
        close_calls.append("db")

    with (
        patch("app.main.db.init_pool", fake_db_init),
        patch("app.main.arq_pool.init_pool", fake_arq_init),
        patch("app.main.arq_pool.close_pool", fake_arq_close),
        patch("app.main.db.close_pool", fake_db_close),
    ):
        async with lifespan(app):
            assert init_calls == ["db", "arq"]

    assert "arq" in close_calls
    assert "db" in close_calls
