"""Unit tests for admin auth middleware and endpoints."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth_router import (
    COOKIE_NAME,
    SESSION_TTL,
    AdminAuthMiddleware,
    _sign_cookie,
    _verify_cookie,
)
from app.auth_router import (
    router as auth_router,
)

# ── Test app: router + middleware + a dummy protected endpoint ────────────────

_app = FastAPI()
_app.add_middleware(AdminAuthMiddleware)
_app.include_router(auth_router)


@_app.get("/admin/stats")
async def _dummy_stats():
    return {"ok": True}


# ── Fixtures & helpers ────────────────────────────────────────────────────────

TEST_PASSWORD = "hunter2"
TEST_SECRET = "deadbeef" * 8  # 64-char hex string


def _bcrypt_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


def _make_pool(config: dict):
    """Return a mock pool backed by an in-memory config dict."""
    conn = AsyncMock()

    async def _fetchrow(query, key):
        if key in config:
            return {"value": config[key]}
        return None

    async def _execute(query, key, value):
        config[key] = value

    conn.fetchrow = _fetchrow
    conn.execute = _execute

    pool = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=_app), base_url="http://test")


# ── Cookie signing unit tests ─────────────────────────────────────────────────


def test_sign_and_verify_cookie():
    token = _sign_cookie(TEST_SECRET)
    assert _verify_cookie(TEST_SECRET, token)


def test_cookie_wrong_secret():
    token = _sign_cookie(TEST_SECRET)
    assert not _verify_cookie("wrong-secret", token)


def test_cookie_expired(monkeypatch):
    old_time = time.time() - SESSION_TTL - 1
    token = f"{int(old_time)}.fakesig"
    assert not _verify_cookie(TEST_SECRET, token)


def test_cookie_tampered():
    token = _sign_cookie(TEST_SECRET)
    ts, _ = token.split(".", 1)
    assert not _verify_cookie(TEST_SECRET, f"{ts}.badhex")


# ── Middleware ────────────────────────────────────────────────────────────────


async def test_middleware_blocks_unauthenticated(client):
    config = {"session_secret": TEST_SECRET}
    pool = _make_pool(config)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/stats")
    assert r.status_code == 401
    assert r.json() == {"detail": "Unauthorized"}


async def test_middleware_allows_valid_cookie(client):
    config = {"session_secret": TEST_SECRET}
    pool = _make_pool(config)
    token = _sign_cookie(TEST_SECRET)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/stats", cookies={COOKIE_NAME: token})
    assert r.status_code == 200


async def test_middleware_allows_valid_basic_auth(client):
    import base64
    pw_hash = _bcrypt_hash(TEST_PASSWORD)
    config = {"session_secret": TEST_SECRET, "admin_password_hash": pw_hash}
    pool = _make_pool(config)
    creds = base64.b64encode(f"admin:{TEST_PASSWORD}".encode()).decode()
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get(
                "/admin/stats", headers={"Authorization": f"Basic {creds}"}
            )
    assert r.status_code == 200


async def test_middleware_skips_public_paths(client):
    # /admin/auth/status is public — no DB needed
    config = {"session_secret": TEST_SECRET}
    pool = _make_pool(config)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/auth/status")
    # Should reach the handler (not be blocked by middleware)
    assert r.status_code == 200


# ── GET /admin/auth/status ────────────────────────────────────────────────────


async def test_status_setup_required_not_authenticated(client):
    config = {"session_secret": TEST_SECRET}
    pool = _make_pool(config)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/auth/status")
    assert r.status_code == 200
    assert r.json() == {"setup_required": True, "authenticated": False}


async def test_status_authenticated_via_cookie(client):
    pw_hash = _bcrypt_hash(TEST_PASSWORD)
    config = {"session_secret": TEST_SECRET, "admin_password_hash": pw_hash}
    pool = _make_pool(config)
    token = _sign_cookie(TEST_SECRET)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/auth/status", cookies={COOKIE_NAME: token})
    data = r.json()
    assert data["setup_required"] is False
    assert data["authenticated"] is True


# ── PUT /admin/auth/setup ─────────────────────────────────────────────────────


async def test_setup_sets_password_and_cookie(client):
    config = {"session_secret": TEST_SECRET}
    pool = _make_pool(config)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.put("/admin/auth/setup", json={"password": TEST_PASSWORD})
    assert r.status_code == 204
    assert COOKIE_NAME in r.cookies
    assert "admin_password_hash" in config


async def test_setup_blocked_after_password_set(client):
    pw_hash = _bcrypt_hash(TEST_PASSWORD)
    config = {"session_secret": TEST_SECRET, "admin_password_hash": pw_hash}
    pool = _make_pool(config)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.put("/admin/auth/setup", json={"password": "newpass"})
    assert r.status_code == 409


# ── POST /admin/auth/login ────────────────────────────────────────────────────


async def test_login_correct_password(client):
    pw_hash = _bcrypt_hash(TEST_PASSWORD)
    config = {"session_secret": TEST_SECRET, "admin_password_hash": pw_hash}
    pool = _make_pool(config)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post("/admin/auth/login", json={"password": TEST_PASSWORD})
    assert r.status_code == 200
    assert r.json() == {"authenticated": True}
    assert COOKIE_NAME in r.cookies


async def test_login_wrong_password(client):
    pw_hash = _bcrypt_hash(TEST_PASSWORD)
    config = {"session_secret": TEST_SECRET, "admin_password_hash": pw_hash}
    pool = _make_pool(config)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        with patch("app.auth_router.asyncio.sleep", AsyncMock()):
            async with client as c:
                r = await c.post("/admin/auth/login", json={"password": "wrongpass"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Unauthorized"}


async def test_login_no_password_set(client):
    config = {"session_secret": TEST_SECRET}
    pool = _make_pool(config)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        with patch("app.auth_router.asyncio.sleep", AsyncMock()):
            async with client as c:
                r = await c.post("/admin/auth/login", json={"password": TEST_PASSWORD})
    assert r.status_code == 401


# ── POST /admin/auth/logout ───────────────────────────────────────────────────


async def test_logout_clears_cookie(client):
    config = {"session_secret": TEST_SECRET}
    pool = _make_pool(config)
    token = _sign_cookie(TEST_SECRET)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                "/admin/auth/logout",
                cookies={COOKIE_NAME: token},
            )
    assert r.status_code == 204
    # Cookie should be cleared (max-age=0 or deleted)
    assert r.cookies.get(COOKIE_NAME) in (None, "")


# ── POST /admin/auth/change-password ─────────────────────────────────────────


async def test_change_password_success(client):
    pw_hash = _bcrypt_hash(TEST_PASSWORD)
    config = {"session_secret": TEST_SECRET, "admin_password_hash": pw_hash}
    pool = _make_pool(config)
    token = _sign_cookie(TEST_SECRET)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                "/admin/auth/change-password",
                json={"current_password": TEST_PASSWORD, "new_password": "newpassword"},
                cookies={COOKIE_NAME: token},
            )
    assert r.status_code == 204
    # New hash stored in config
    assert bcrypt.checkpw(b"newpassword", config["admin_password_hash"].encode())


async def test_change_password_wrong_current(client):
    pw_hash = _bcrypt_hash(TEST_PASSWORD)
    config = {"session_secret": TEST_SECRET, "admin_password_hash": pw_hash}
    pool = _make_pool(config)
    token = _sign_cookie(TEST_SECRET)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                "/admin/auth/change-password",
                json={"current_password": "wrongpass", "new_password": "new"},
                cookies={COOKIE_NAME: token},
            )
    assert r.status_code == 401


async def test_change_password_requires_auth(client):
    pw_hash = _bcrypt_hash(TEST_PASSWORD)
    config = {"session_secret": TEST_SECRET, "admin_password_hash": pw_hash}
    pool = _make_pool(config)
    with patch("app.auth_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                "/admin/auth/change-password",
                json={"current_password": TEST_PASSWORD, "new_password": "new"},
                # No cookie — middleware should block this
            )
    assert r.status_code == 401
