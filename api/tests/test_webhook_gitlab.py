import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

SECRET = "gitlab-secret"

MR_OPEN_PAYLOAD = {
    "object_kind": "merge_request",
    "object_attributes": {
        "id": 100,
        "iid": 1,
        "action": "open",
        "title": "Add feature",
        "updated_at": "2026-04-21T00:00:00Z",
    },
    "project": {
        "id": 5,
        "path_with_namespace": "group/repo",
    },
}

MR_CLOSE_PAYLOAD = {**MR_OPEN_PAYLOAD, "object_attributes": {**MR_OPEN_PAYLOAD["object_attributes"], "action": "close"}}


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
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", SECRET)


@pytest.fixture()
async def client(mock_db_pool, mock_arq_pool):
    with (
        patch("app.webhook.get_db_pool", return_value=mock_db_pool),
        patch("app.webhook.get_arq_pool", return_value=mock_arq_pool),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


def _headers(secret: str = SECRET, event: str = "Merge Request Hook") -> dict:
    return {
        "X-Gitlab-Token": secret,
        "X-Gitlab-Event": event,
        "Content-Type": "application/json",
    }


class TestGitLabSignatureValidation:
    async def test_wrong_token_returns_401(self, client, env_secret):
        body = json.dumps(MR_OPEN_PAYLOAD).encode()
        resp = await client.post("/webhook/gitlab", content=body, headers=_headers("wrong"))
        assert resp.status_code == 401

    async def test_missing_token_returns_401(self, client, env_secret):
        body = json.dumps(MR_OPEN_PAYLOAD).encode()
        headers = {"X-Gitlab-Event": "Merge Request Hook", "Content-Type": "application/json"}
        resp = await client.post("/webhook/gitlab", content=body, headers=headers)
        assert resp.status_code == 401

    async def test_no_secret_configured_rejects(self, client, monkeypatch):
        monkeypatch.delenv("GITLAB_WEBHOOK_SECRET", raising=False)
        body = json.dumps(MR_OPEN_PAYLOAD).encode()
        resp = await client.post("/webhook/gitlab", content=body, headers=_headers())
        assert resp.status_code == 401


class TestGitLabEventFiltering:
    async def test_non_mr_event_returns_200_ignored(self, client, env_secret):
        body = json.dumps({"object_kind": "push"}).encode()
        resp = await client.post(
            "/webhook/gitlab", content=body, headers=_headers(event="Push Hook")
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    async def test_mr_close_action_returns_200_ignored(self, client, env_secret):
        body = json.dumps(MR_CLOSE_PAYLOAD).encode()
        resp = await client.post("/webhook/gitlab", content=body, headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"


class TestGitLabIdempotency:
    async def test_new_mr_open_returns_202_and_enqueues(
        self, client, env_secret, mock_db_conn, mock_arq_pool
    ):
        mock_db_conn.fetchrow = AsyncMock(return_value=MagicMock())
        body = json.dumps(MR_OPEN_PAYLOAD).encode()
        resp = await client.post("/webhook/gitlab", content=body, headers=_headers())
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"
        mock_arq_pool.enqueue_job.assert_awaited_once()
        job_args = mock_arq_pool.enqueue_job.call_args[0]
        assert job_args[0] == "process_webhook"

    async def test_duplicate_delivery_returns_200_no_enqueue(
        self, client, env_secret, mock_db_conn, mock_arq_pool
    ):
        mock_db_conn.fetchrow = AsyncMock(return_value=None)  # ON CONFLICT → None
        body = json.dumps(MR_OPEN_PAYLOAD).encode()
        resp = await client.post("/webhook/gitlab", content=body, headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["status"] == "duplicate"
        mock_arq_pool.enqueue_job.assert_not_awaited()
