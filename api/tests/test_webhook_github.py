import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

SECRET = "gh-test-secret"
DELIVERY_ID = "gh-delivery-001"

PR_PAYLOAD = {
    "action": "opened",
    "pull_request": {"number": 42, "title": "feat: add thing"},
    "repository": {"full_name": "org/repo"},
}


def _sig(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _valid_headers(body: bytes, secret: str = SECRET) -> dict:
    return {
        "X-GitHub-Delivery": DELIVERY_ID,
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": _sig(body, secret),
        "Content-Type": "application/json",
    }


@pytest.fixture()
def mock_db_conn():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=MagicMock(delivery_id=DELIVERY_ID))
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


@pytest.fixture()
async def client(mock_db_pool, mock_arq_pool):
    with (
        patch("app.webhook.get_db_pool", return_value=mock_db_pool),
        patch("app.webhook.get_arq_pool", return_value=mock_arq_pool),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest.fixture()
def env_secret(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)


class TestGitHubSignatureValidation:
    async def test_wrong_signature_returns_401(self, client, env_secret):
        body = json.dumps(PR_PAYLOAD).encode()
        resp = await client.post(
            "/webhook/github",
            content=body,
            headers=_valid_headers(body, secret="wrong-secret"),
        )
        assert resp.status_code == 401

    async def test_missing_signature_header_returns_401(self, client, env_secret):
        body = json.dumps(PR_PAYLOAD).encode()
        headers = {
            "X-GitHub-Delivery": DELIVERY_ID,
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        }
        resp = await client.post("/webhook/github", content=body, headers=headers)
        assert resp.status_code == 401

    async def test_missing_secret_env_returns_401(self, client, monkeypatch):
        monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
        body = json.dumps(PR_PAYLOAD).encode()
        resp = await client.post(
            "/webhook/github", content=body, headers=_valid_headers(body)
        )
        assert resp.status_code == 401

    async def test_valid_signature_returns_202(self, client, env_secret):
        body = json.dumps(PR_PAYLOAD).encode()
        resp = await client.post(
            "/webhook/github", content=body, headers=_valid_headers(body)
        )
        assert resp.status_code == 202
        assert resp.json()["status"] == "accepted"
