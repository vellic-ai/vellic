import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

DELIVERY_ID = "abc-123"
SECRET = "test-secret"
PR_PAYLOAD = {
    "action": "opened",
    "pull_request": {"number": 1, "title": "feat: test"},
    "repository": {"full_name": "org/repo"},
}
REVIEW_PAYLOAD = {
    "action": "submitted",
    "review": {"state": "approved"},
    "pull_request": {"number": 1},
    "repository": {"full_name": "org/repo"},
}


def _sig(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _pr_headers(
    body: bytes,
    event: str = "pull_request",
    delivery_id: str = DELIVERY_ID,
    secret: str = SECRET,
) -> dict:
    return {
        "X-GitHub-Delivery": delivery_id,
        "X-GitHub-Event": event,
        "X-Hub-Signature-256": _sig(body, secret),
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


@pytest.fixture()
def env_secret(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)


@pytest.fixture()
async def client(mock_db_pool, mock_arq_pool):
    with (
        patch("app.webhook.get_db_pool", return_value=mock_db_pool),
        patch("app.webhook.get_arq_pool", return_value=mock_arq_pool),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


class TestSignatureValidation:
    async def test_invalid_signature_returns_400(self, client, env_secret):
        body = json.dumps(PR_PAYLOAD).encode()
        headers = _pr_headers(body, secret="wrong-secret")
        resp = await client.post("/webhook/github", content=body, headers=headers)
        assert resp.status_code == 400

    async def test_missing_signature_with_secret_returns_400(self, client, env_secret):
        body = json.dumps(PR_PAYLOAD).encode()
        headers = {
            "X-GitHub-Delivery": DELIVERY_ID,
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        }
        resp = await client.post("/webhook/github", content=body, headers=headers)
        assert resp.status_code == 400

    async def test_no_secret_configured_rejects(self, client, monkeypatch):
        monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
        body = json.dumps(PR_PAYLOAD).encode()
        headers = {
            "X-GitHub-Delivery": DELIVERY_ID,
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        }
        resp = await client.post("/webhook/github", content=body, headers=headers)
        assert resp.status_code == 400


class TestEventFiltering:
    async def test_unhandled_event_returns_200(self, client, env_secret):
        body = json.dumps({"action": "created"}).encode()
        headers = _pr_headers(body, event="issues")
        resp = await client.post("/webhook/github", content=body, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    async def test_pr_filtered_action_returns_200(self, client, env_secret):
        payload = {**PR_PAYLOAD, "action": "closed"}
        body = json.dumps(payload).encode()
        headers = _pr_headers(body, event="pull_request")
        resp = await client.post("/webhook/github", content=body, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    async def test_pull_request_review_accepted(
        self, client, env_secret, mock_db_conn, mock_arq_pool
    ):
        mock_db_conn.fetchrow = AsyncMock(return_value=MagicMock(delivery_id=DELIVERY_ID))
        body = json.dumps(REVIEW_PAYLOAD).encode()
        headers = _pr_headers(body, event="pull_request_review", delivery_id="review-1")
        resp = await client.post("/webhook/github", content=body, headers=headers)
        assert resp.status_code == 202


class TestIdempotency:
    async def test_new_delivery_returns_202_and_enqueues(
        self, client, env_secret, mock_db_conn, mock_arq_pool
    ):
        mock_db_conn.fetchrow = AsyncMock(return_value=MagicMock(delivery_id=DELIVERY_ID))
        body = json.dumps(PR_PAYLOAD).encode()
        headers = _pr_headers(body)
        resp = await client.post("/webhook/github", content=body, headers=headers)
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["delivery_id"] == DELIVERY_ID
        mock_arq_pool.enqueue_job.assert_awaited_once_with("process_webhook", DELIVERY_ID)

    async def test_duplicate_delivery_returns_200_no_enqueue(
        self, client, env_secret, mock_db_conn, mock_arq_pool
    ):
        mock_db_conn.fetchrow = AsyncMock(return_value=None)  # ON CONFLICT → None
        body = json.dumps(PR_PAYLOAD).encode()
        headers = _pr_headers(body, delivery_id="dup-999")
        resp = await client.post("/webhook/github", content=body, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "duplicate"
        mock_arq_pool.enqueue_job.assert_not_awaited()

    async def test_missing_delivery_id_returns_400(self, client, env_secret):
        body = json.dumps(PR_PAYLOAD).encode()
        headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": _sig(body),
            "Content-Type": "application/json",
        }
        resp = await client.post("/webhook/github", content=body, headers=headers)
        assert resp.status_code == 400
