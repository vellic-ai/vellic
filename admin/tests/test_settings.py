"""Unit tests for GET/PUT /admin/settings/llm."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.settings_router import router

# Minimal app — no lifespan so no real DB/ARQ connections needed in tests.
_app = FastAPI()
_app.include_router(router)

TEST_KEY = Fernet.generate_key().decode()
_FIXED_TS = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def fernet_env(monkeypatch):
    monkeypatch.setenv("LLM_ENCRYPTION_KEY", TEST_KEY)


def _make_pool(fetchrow_result):
    """Return a mock asyncpg pool whose acquire() context manager yields a conn."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    pool = MagicMock()
    acquire_ctx = MagicMock()
    acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
    acquire_ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = acquire_ctx
    return pool, conn


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=_app), base_url="http://test")


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


async def test_get_not_found(client, monkeypatch):
    pool, _ = _make_pool(None)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/settings/llm")
    assert r.status_code == 404


async def test_get_returns_masked_key(client, monkeypatch):
    from app.crypto import encrypt

    encrypted = encrypt("sk-secretvalue")
    row = {
        "provider": "openai",
        "base_url": None,
        "model": "gpt-4o",
        "api_key": encrypted,
        "extra": {},
        "updated_at": _FIXED_TS,
    }
    pool, _ = _make_pool(row)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/settings/llm")
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "openai"
    assert data["api_key"] == "sk-s****"
    assert "secretvalue" not in data["api_key"]


async def test_get_no_api_key(client):
    row = {
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "model": "llama3",
        "api_key": None,
        "extra": {"timeout": 30},
        "updated_at": _FIXED_TS,
    }
    pool, _ = _make_pool(row)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.get("/admin/settings/llm")
    assert r.status_code == 200
    data = r.json()
    assert data["api_key"] is None
    assert data["extra"] == {"timeout": 30}


# ---------------------------------------------------------------------------
# PUT
# ---------------------------------------------------------------------------


async def test_put_rejects_unknown_provider(client):
    async with client as c:
        r = await c.put(
            "/admin/settings/llm",
            json={"provider": "bedrock", "model": "claude-v2"},
        )
    assert r.status_code == 422


async def test_put_valid_upsert(client):
    row = {
        "provider": "anthropic",
        "base_url": None,
        "model": "claude-sonnet-4-6",
        "api_key": "encrypted-placeholder",
        "extra": {},
        "updated_at": _FIXED_TS,
    }
    pool, _ = _make_pool(row)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.put(
                "/admin/settings/llm",
                json={
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-6",
                    "api_key": "sk-ant-hello",
                },
            )
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "anthropic"
    # Masked key uses plaintext passed in the body
    assert data["api_key"].startswith("sk-a")
    assert "hello" not in data["api_key"]


async def test_put_no_api_key(client):
    row = {
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "model": "llama3",
        "api_key": None,
        "extra": {},
        "updated_at": _FIXED_TS,
    }
    pool, _ = _make_pool(row)
    with patch("app.settings_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.put(
                "/admin/settings/llm",
                json={
                    "provider": "ollama",
                    "base_url": "http://localhost:11434",
                    "model": "llama3",
                },
            )
    assert r.status_code == 200
    assert r.json()["api_key"] is None


# ---------------------------------------------------------------------------
# Masking unit test (independent of HTTP layer)
# ---------------------------------------------------------------------------


def test_mask_short_key():
    from app.crypto import mask

    assert mask("ab") == "ab****"


def test_mask_long_key():
    from app.crypto import mask

    result = mask("sk-abcdefgh")
    assert result == "sk-a****"
    assert "efgh" not in result


def test_encrypt_decrypt_roundtrip():
    from app.crypto import decrypt, encrypt

    original = "super-secret-key-123"
    assert decrypt(encrypt(original)) == original
