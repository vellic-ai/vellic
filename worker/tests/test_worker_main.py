"""Tests for worker/app/main.py — HealthHandler, startup, shutdown."""

import io
from http.server import BaseHTTPRequestHandler
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import HealthHandler, shutdown, startup


# ---------------------------------------------------------------------------
# HealthHandler
# ---------------------------------------------------------------------------

def _make_handler(path: str) -> HealthHandler:
    """Construct a HealthHandler without a real socket."""
    handler = HealthHandler.__new__(HealthHandler)
    handler.path = path
    handler.wfile = io.BytesIO()
    handler._headers_buffer = []
    handler.requestline = ""
    handler.client_address = ("127.0.0.1", 0)
    return handler


class TestHealthHandler:
    def test_health_path_sends_200(self):
        handler = _make_handler("/health")
        responses = []

        def fake_send_response(code):
            responses.append(code)

        handler.send_response = fake_send_response
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_GET()

        assert responses == [200]
        body = handler.wfile.getvalue()
        assert b'"status":"ok"' in body
        assert b'"service":"worker"' in body

    def test_unknown_path_sends_404(self):
        handler = _make_handler("/unknown")
        responses = []

        def fake_send_response(code):
            responses.append(code)

        handler.send_response = fake_send_response
        handler.end_headers = MagicMock()

        handler.do_GET()

        assert responses == [404]

    def test_log_message_is_silent(self):
        """log_message must not raise (it's intentionally suppressed)."""
        handler = _make_handler("/health")
        handler.log_message("GET %s %s", "/health", "200")  # should not raise


# ---------------------------------------------------------------------------
# startup / shutdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_startup_populates_ctx():
    ctx: dict = {}
    fake_pool = MagicMock()
    fake_arq = MagicMock()

    with (
        patch("app.main.asyncpg.create_pool", new=AsyncMock(return_value=fake_pool)),
        patch("app.main.arq_create_pool", new=AsyncMock(return_value=fake_arq)),
        patch.dict("os.environ", {"DATABASE_URL": "postgresql://user:pass@localhost/db"}),
    ):
        await startup(ctx)

    assert ctx["db_pool"] is fake_pool
    assert ctx["redis"] is fake_arq


@pytest.mark.asyncio
async def test_shutdown_closes_pools():
    fake_arq = AsyncMock()
    fake_pool = AsyncMock()
    ctx = {"redis": fake_arq, "db_pool": fake_pool}

    await shutdown(ctx)

    fake_arq.close.assert_called_once()
    fake_pool.close.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_handles_missing_pools():
    """shutdown must not raise when ctx keys are absent."""
    await shutdown({})
