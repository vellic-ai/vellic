"""Tests for per-IP sliding-window rate limiting on webhook endpoints."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import rate_limit as rl_module
from app.main import app

SECRET = "test-secret"
PR_PAYLOAD = {
    "action": "opened",
    "pull_request": {"number": 1, "title": "feat: test"},
    "repository": {"full_name": "org/repo"},
}


def _sig(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def _gh_headers(body: bytes, delivery_id: str = "d1") -> dict:
    return {
        "X-GitHub-Delivery": delivery_id,
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": _sig(body),
        "Content-Type": "application/json",
    }


@pytest.fixture()
def mock_db_conn():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=MagicMock(spec=["__getitem__"]))
    return conn


@pytest.fixture()
def mock_db_pool(mock_db_conn):
    pool = MagicMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_db_conn),
            __aexit__=AsyncMock(return_value=False),
        )
    )
    return pool


@pytest.fixture()
def mock_arq_pool():
    pool = AsyncMock()
    pool.enqueue_job = AsyncMock()
    return pool


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear the in-process counter between tests."""
    rl_module._counters.clear()
    yield
    rl_module._counters.clear()


@pytest.fixture()
def low_limit(monkeypatch):
    """Set limit to 2 requests per window so tests run fast."""
    monkeypatch.setattr(rl_module, "_LIMIT", 2)


@pytest.fixture()
async def client(mock_db_pool, mock_arq_pool):
    with (
        patch("app.webhook.get_db_pool", return_value=mock_db_pool),
        patch("app.webhook.get_arq_pool", return_value=mock_arq_pool),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


class TestRateLimiting:
    async def test_within_limit_returns_non_429(
        self, client, low_limit, monkeypatch, mock_db_conn, mock_arq_pool
    ):
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
        mock_db_conn.fetchrow = AsyncMock(return_value=MagicMock())
        body = json.dumps(PR_PAYLOAD).encode()

        for i in range(2):
            resp = await client.post(
                "/webhook/github",
                content=body,
                headers=_gh_headers(body, delivery_id=f"d{i}"),
            )
            assert resp.status_code != 429, f"request {i} was rate-limited unexpectedly"

    async def test_exceeding_limit_returns_429(
        self, client, low_limit, monkeypatch, mock_db_conn, mock_arq_pool
    ):
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
        mock_db_conn.fetchrow = AsyncMock(return_value=MagicMock())
        body = json.dumps(PR_PAYLOAD).encode()

        for i in range(2):
            await client.post(
                "/webhook/github",
                content=body,
                headers=_gh_headers(body, delivery_id=f"d{i}"),
            )

        resp = await client.post(
            "/webhook/github",
            content=body,
            headers=_gh_headers(body, delivery_id="d999"),
        )
        assert resp.status_code == 429

    async def test_429_response_includes_retry_after(
        self, client, low_limit, monkeypatch, mock_db_conn, mock_arq_pool
    ):
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
        mock_db_conn.fetchrow = AsyncMock(return_value=MagicMock())
        body = json.dumps(PR_PAYLOAD).encode()

        for i in range(3):
            resp = await client.post(
                "/webhook/github",
                content=body,
                headers=_gh_headers(body, delivery_id=f"d{i}"),
            )

        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    async def test_rate_limit_applied_to_gitlab_endpoint(self, client, low_limit, monkeypatch):
        monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", "gl-secret")
        payload = json.dumps({"object_kind": "push"}).encode()
        headers = {
            "X-Gitlab-Token": "gl-secret",
            "X-Gitlab-Event": "Push Hook",
            "Content-Type": "application/json",
        }
        for _ in range(2):
            await client.post("/webhook/gitlab", content=payload, headers=headers)
        resp = await client.post("/webhook/gitlab", content=payload, headers=headers)
        assert resp.status_code == 429

    async def test_rate_limit_applied_to_bitbucket_endpoint(
        self, client, low_limit, monkeypatch
    ):
        import hashlib as hl
        import hmac as hm

        monkeypatch.setenv("BITBUCKET_WEBHOOK_SECRET", "bb-secret")
        bb_secret = "bb-secret"
        payload = json.dumps({"event": "pullrequest:created"}).encode()
        sig = "sha256=" + hm.new(bb_secret.encode(), payload, hl.sha256).hexdigest()
        headers = {
            "X-Event-Key": "pullrequest:created",
            "X-Hub-Signature": sig,
            "X-Request-UUID": "bb-uuid-1",
            "Content-Type": "application/json",
        }
        for _ in range(2):
            await client.post("/webhook/bitbucket", content=payload, headers=headers)
        resp = await client.post("/webhook/bitbucket", content=payload, headers=headers)
        assert resp.status_code == 429
