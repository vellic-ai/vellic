import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

SECRET = "bb-secret"

PR_CREATED_PAYLOAD = {
    "pullrequest": {
        "id": 42,
        "title": "Add feature",
        "description": "Desc",
        "source": {
            "commit": {"hash": "aabbcc"},
            "branch": {"name": "feat"},
        },
        "destination": {
            "commit": {"hash": "112233"},
            "branch": {"name": "main"},
        },
        "links": {"diff": {"href": "https://api.bitbucket.org/2.0/repositories/org/repo/pullrequests/42/diff"}},
    },
    "repository": {"full_name": "org/repo"},
}

PR_FULFILLED_PAYLOAD = {**PR_CREATED_PAYLOAD}


def _sig(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


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


@pytest.fixture()
def env_secret(monkeypatch):
    monkeypatch.setenv("BITBUCKET_WEBHOOK_SECRET", SECRET)


@pytest.fixture()
async def client(mock_db_pool, mock_arq_pool):
    with (
        patch("app.webhook.get_db_pool", return_value=mock_db_pool),
        patch("app.webhook.get_arq_pool", return_value=mock_arq_pool),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


def _headers(
    body: bytes,
    event: str = "pullrequest:created",
    secret: str = SECRET,
    uuid: str = "test-uuid-1",
) -> dict:
    return {
        "X-Event-Key": event,
        "X-Hub-Signature": _sig(body, secret),
        "X-Request-UUID": uuid,
        "Content-Type": "application/json",
    }


class TestBitbucketSignatureValidation:
    async def test_wrong_signature_returns_401(self, client, env_secret):
        body = json.dumps(PR_CREATED_PAYLOAD).encode()
        headers = _headers(body, secret="wrong-secret")
        resp = await client.post("/webhook/bitbucket", content=body, headers=headers)
        assert resp.status_code == 401

    async def test_missing_signature_returns_401(self, client, env_secret):
        body = json.dumps(PR_CREATED_PAYLOAD).encode()
        resp = await client.post(
            "/webhook/bitbucket",
            content=body,
            headers={"X-Event-Key": "pullrequest:created", "Content-Type": "application/json"},
        )
        assert resp.status_code == 401

    async def test_no_secret_configured_rejects(self, client, monkeypatch):
        monkeypatch.delenv("BITBUCKET_WEBHOOK_SECRET", raising=False)
        body = json.dumps(PR_CREATED_PAYLOAD).encode()
        resp = await client.post("/webhook/bitbucket", content=body, headers=_headers(body))
        assert resp.status_code == 401


class TestBitbucketEventFiltering:
    async def test_unhandled_event_returns_200_ignored(self, client, env_secret):
        body = json.dumps({"repository": {}}).encode()
        resp = await client.post(
            "/webhook/bitbucket",
            content=body,
            headers=_headers(body, event="pullrequest:rejected"),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    async def test_pr_fulfilled_returns_202(self, client, env_secret, mock_db_conn, mock_arq_pool):
        body = json.dumps(PR_FULFILLED_PAYLOAD).encode()
        resp = await client.post(
            "/webhook/bitbucket",
            content=body,
            headers=_headers(body, event="pullrequest:fulfilled"),
        )
        assert resp.status_code == 202

    async def test_pr_updated_returns_202(self, client, env_secret, mock_db_conn, mock_arq_pool):
        body = json.dumps(PR_CREATED_PAYLOAD).encode()
        resp = await client.post(
            "/webhook/bitbucket",
            content=body,
            headers=_headers(body, event="pullrequest:updated"),
        )
        assert resp.status_code == 202


class TestBitbucketIdempotency:
    async def test_new_pr_returns_202_and_enqueues(
        self, client, env_secret, mock_db_conn, mock_arq_pool
    ):
        mock_db_conn.fetchrow = AsyncMock(return_value=MagicMock())
        body = json.dumps(PR_CREATED_PAYLOAD).encode()
        resp = await client.post("/webhook/bitbucket", content=body, headers=_headers(body))
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["delivery_id"] == "test-uuid-1"
        mock_arq_pool.enqueue_job.assert_awaited_once()
        assert mock_arq_pool.enqueue_job.call_args[0][0] == "process_webhook"

    async def test_duplicate_delivery_returns_200_no_enqueue(
        self, client, env_secret, mock_db_conn, mock_arq_pool
    ):
        mock_db_conn.fetchrow = AsyncMock(return_value=None)  # ON CONFLICT → None
        body = json.dumps(PR_CREATED_PAYLOAD).encode()
        resp = await client.post("/webhook/bitbucket", content=body, headers=_headers(body))
        assert resp.status_code == 200
        assert resp.json()["status"] == "duplicate"
        mock_arq_pool.enqueue_job.assert_not_awaited()

    async def test_missing_uuid_header_generates_delivery_id(
        self, client, env_secret, mock_db_conn, mock_arq_pool
    ):
        body = json.dumps(PR_CREATED_PAYLOAD).encode()
        headers = {
            "X-Event-Key": "pullrequest:created",
            "X-Hub-Signature": _sig(body),
            "Content-Type": "application/json",
        }
        resp = await client.post("/webhook/bitbucket", content=body, headers=headers)
        assert resp.status_code == 202
        assert resp.json()["delivery_id"].startswith("bb-")
