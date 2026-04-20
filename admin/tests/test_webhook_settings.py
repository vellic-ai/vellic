"""Tests for webhook settings API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.settings_router import router

_app = FastAPI()
_app.include_router(router)

TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def fernet_env(monkeypatch):
    monkeypatch.setenv("LLM_ENCRYPTION_KEY", TEST_KEY)


def _make_pool(fetchrow_result=None, execute_result=None):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.execute = AsyncMock(return_value=execute_result)
    pool = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool, conn


def _make_db_row(**kwargs):
    defaults = {
        "url": None,
        "hmac": None,
        "github_app_id": None,
        "github_installation_id": None,
        "github_private_key": None,
        "gitlab_token": None,
    }
    defaults.update(kwargs)
    return defaults


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=_app), base_url="http://test")


# ---------------------------------------------------------------------------
# GET /admin/settings/webhook
# ---------------------------------------------------------------------------

async def test_get_webhook_not_found(client):
    pool, _ = _make_pool(None)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/settings/webhook")
    assert r.status_code == 404


async def test_get_webhook_empty_config(client):
    from app.crypto import encrypt

    hmac_val = "whsec_abc123"
    row = _make_db_row(url="https://example.com/hook", hmac=encrypt(hmac_val))
    pool, _ = _make_pool(row)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/settings/webhook")
    assert r.status_code == 200
    data = r.json()
    assert data["url"] == "https://example.com/hook"
    assert data["hmac"] == hmac_val
    assert data["github_key_set"] is False
    assert data["gitlab_token_set"] is False


async def test_get_webhook_with_secrets_set(client):
    from app.crypto import encrypt

    row = _make_db_row(
        url="https://hook.example.com",
        hmac=encrypt("whsec_xyz"),
        github_app_id="12345",
        github_installation_id="67890",
        github_private_key=encrypt(
            "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----"
        ),
        gitlab_token=encrypt("glpat-abc"),
    )
    pool, _ = _make_pool(row)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/settings/webhook")
    assert r.status_code == 200
    data = r.json()
    assert data["github_key_set"] is True
    assert data["gitlab_token_set"] is True
    assert data["github_app_id"] == "12345"


# ---------------------------------------------------------------------------
# PUT /admin/settings/webhook
# ---------------------------------------------------------------------------

async def test_put_webhook_url(client):
    from app.crypto import encrypt

    row = _make_db_row(url="https://new.example.com/hook", hmac=encrypt("whsec_old"))
    pool, _ = _make_pool(row)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.put("/admin/settings/webhook", json={"url": "https://new.example.com/hook"})
    assert r.status_code == 200
    assert r.json()["url"] == "https://new.example.com/hook"


# ---------------------------------------------------------------------------
# POST /admin/settings/webhook/rotate
# ---------------------------------------------------------------------------

async def test_rotate_hmac(client):
    pool, conn = _make_pool()
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post("/admin/settings/webhook/rotate")
    assert r.status_code == 200
    data = r.json()
    assert data["hmac"].startswith("whsec_")
    conn.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# PUT /admin/settings/github
# ---------------------------------------------------------------------------

async def test_put_github_no_key(client):
    from app.crypto import encrypt

    row = _make_db_row(
        github_app_id="111",
        github_installation_id="222",
        github_private_key=encrypt("existing-key"),
    )
    pool, _ = _make_pool(row)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.put(
                "/admin/settings/github",
                json={"app_id": "111", "installation_id": "222"},
            )
    assert r.status_code == 200
    assert r.json()["github_app_id"] == "111"
    assert r.json()["github_key_set"] is True


async def test_put_github_with_key(client):
    from app.crypto import encrypt

    row = _make_db_row(
        github_app_id="999",
        github_installation_id="888",
        github_private_key=encrypt(
            "-----BEGIN RSA PRIVATE KEY-----\nnewkey\n-----END RSA PRIVATE KEY-----"
        ),
    )
    pool, _ = _make_pool(row)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.put(
                "/admin/settings/github",
                json={
                    "app_id": "999",
                    "installation_id": "888",
                    "private_key": (
                        "-----BEGIN RSA PRIVATE KEY-----\nnewkey\n-----END RSA PRIVATE KEY-----"
                    ),
                },
            )
    assert r.status_code == 200
    assert r.json()["github_key_set"] is True


# ---------------------------------------------------------------------------
# POST /admin/settings/github/test
# ---------------------------------------------------------------------------

async def test_github_test_not_configured(client):
    pool, _ = _make_pool(_make_db_row())
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post("/admin/settings/github/test")
    assert r.status_code == 422


async def test_github_test_ok(client):
    from app.crypto import encrypt

    row = _make_db_row(
        github_app_id="12345",
        github_installation_id="67890",
        github_private_key=encrypt("fake-pem"),
    )
    pool, _ = _make_pool(row)

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.settings_router.db.get_pool", return_value=pool),
        patch("app.settings_router.httpx.AsyncClient", return_value=mock_client),
    ):
        with patch("jwt.encode", return_value="fake-token"):
            async with client as c:
                r = await c.post("/admin/settings/github/test")
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ---------------------------------------------------------------------------
# PUT /admin/settings/gitlab
# ---------------------------------------------------------------------------

async def test_put_gitlab_no_token_rejected(client):
    async with client as c:
        r = await c.put("/admin/settings/gitlab", json={})
    assert r.status_code == 422


async def test_put_gitlab_with_token(client):
    from app.crypto import encrypt

    row = _make_db_row(gitlab_token=encrypt("glpat-newtoken"))
    pool, _ = _make_pool(row)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.put("/admin/settings/gitlab", json={"token": "glpat-newtoken"})
    assert r.status_code == 200
    assert r.json()["gitlab_token_set"] is True


# ---------------------------------------------------------------------------
# POST /admin/settings/gitlab/test
# ---------------------------------------------------------------------------

async def test_gitlab_test_not_configured(client):
    pool, _ = _make_pool(_make_db_row())
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post("/admin/settings/gitlab/test")
    assert r.status_code == 422


async def test_gitlab_test_ok(client):
    from app.crypto import encrypt

    row = _make_db_row(gitlab_token=encrypt("glpat-abc"))
    pool, _ = _make_pool(row)

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.settings_router.db.get_pool", return_value=pool),
        patch("app.settings_router.httpx.AsyncClient", return_value=mock_client),
    ):
        async with client as c:
            r = await c.post("/admin/settings/gitlab/test")
    assert r.status_code == 200
    assert r.json()["ok"] is True
