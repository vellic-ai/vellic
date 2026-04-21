"""Tests for GET/PUT/test /api/repos/{repo_id}/llm-config."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient

from app.main import app

_NOW = datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC)
_FERNET_KEY = Fernet.generate_key().decode()
_INSTALLATION_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_CONFIG_ID = "bbbbbbbb-0000-0000-0000-000000000002"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_flag_enabled():
    """Enable platform.llm_config_ui for all tests in this module."""
    with patch("app.llm_config_router._require_flag", new=AsyncMock(return_value=None)):
        yield


@pytest.fixture()
def enc_key(monkeypatch):
    monkeypatch.setenv("LLM_ENCRYPTION_KEY", _FERNET_KEY)
    return _FERNET_KEY


def _encrypt(plaintext: str, key: str) -> str:
    return Fernet(key.encode()).encrypt(plaintext.encode()).decode()


class _Row(dict):
    """asyncpg.Record-compatible dict that supports dict(row) correctly."""


def _make_pool(fetchrow_side_effect=None, fetchrow_return=None):
    pool = MagicMock()
    if fetchrow_side_effect is not None:
        pool.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
    else:
        pool.fetchrow = AsyncMock(return_value=fetchrow_return)
    return pool


def _install_row() -> _Row:
    return _Row({"id": _INSTALLATION_ID})


def _config_row(api_key_enc: str | None = None) -> _Row:
    return _Row({
        "id": _CONFIG_ID,
        "installation_id": _INSTALLATION_ID,
        "provider": "openai",
        "model": "gpt-4o",
        "base_url": None,
        "api_key_enc": api_key_enc,
        "created_at": _NOW,
        "updated_at": _NOW,
    })


# ---------------------------------------------------------------------------
# GET /api/repos/{repo_id}/llm-config
# ---------------------------------------------------------------------------

class TestGetLLMConfig:
    @pytest.mark.asyncio
    async def test_returns_404_when_repo_not_found(self, enc_key):
        pool = _make_pool(fetchrow_return=None)
        with patch("app.llm_config_router.db") as mock_db:
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/repos/org/repo/llm-config")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_when_config_not_set(self, enc_key):
        install_row = _install_row()
        pool = _make_pool(fetchrow_side_effect=[install_row, None])
        with patch("app.llm_config_router.db") as mock_db:
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/repos/org/repo/llm-config")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_config_with_masked_api_key(self, enc_key):
        api_key_enc = _encrypt("sk-secret-key", _FERNET_KEY)
        install_row = _install_row()
        cfg_row = _config_row(api_key_enc=api_key_enc)
        pool = _make_pool(fetchrow_side_effect=[install_row, cfg_row])
        with patch("app.llm_config_router.db") as mock_db:
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/repos/org/repo/llm-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4o"
        assert data["api_key"].startswith("sk-s")
        assert "****" in data["api_key"]
        assert "secret" not in data["api_key"]

    @pytest.mark.asyncio
    async def test_returns_config_without_api_key(self, enc_key):
        install_row = _install_row()
        cfg_row = _config_row(api_key_enc=None)
        pool = _make_pool(fetchrow_side_effect=[install_row, cfg_row])
        with patch("app.llm_config_router.db") as mock_db:
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/repos/org/repo/llm-config")
        assert resp.status_code == 200
        assert resp.json()["api_key"] is None

    @pytest.mark.asyncio
    async def test_repo_id_must_be_org_slash_repo(self, enc_key):
        pool = _make_pool(fetchrow_return=None)
        with patch("app.llm_config_router.db") as mock_db:
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/repos/nodash/llm-config")
        # "nodash" has no slash → 422 from _fetch_installation_id
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/repos/{repo_id}/llm-config
# ---------------------------------------------------------------------------

class TestPutLLMConfig:
    @pytest.mark.asyncio
    async def test_rejects_invalid_provider(self, enc_key):
        pool = _make_pool(fetchrow_return=_install_row())
        with patch("app.llm_config_router.db") as mock_db:
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.put(
                    "/api/repos/org/repo/llm-config",
                    json={"provider": "notexist", "model": "x"},
                )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_upserts_config_and_masks_key(self, enc_key):
        install_row = _install_row()
        cfg_row = _config_row(api_key_enc=_encrypt("sk-new-key", _FERNET_KEY))
        pool = _make_pool(fetchrow_side_effect=[install_row, cfg_row])
        with patch("app.llm_config_router.db") as mock_db:
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.put(
                    "/api/repos/org/repo/llm-config",
                    json={"provider": "openai", "model": "gpt-4o", "api_key": "sk-new-key"},
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "openai"
        assert data["api_key"] == "sk-n****"

    @pytest.mark.asyncio
    async def test_upserts_config_without_api_key(self, enc_key):
        install_row = _install_row()
        returned_row = _Row({
            "id": _CONFIG_ID,
            "installation_id": _INSTALLATION_ID,
            "provider": "ollama",
            "model": "llama3",
            "base_url": "http://llm:11434",
            "api_key_enc": None,
            "created_at": _NOW,
            "updated_at": _NOW,
        })
        pool = _make_pool(fetchrow_side_effect=[install_row, returned_row])
        with patch("app.llm_config_router.db") as mock_db:
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.put(
                    "/api/repos/org/repo/llm-config",
                    json={"provider": "ollama", "model": "llama3", "base_url": "http://llm:11434"},
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "llama3"
        assert data["api_key"] is None

    @pytest.mark.asyncio
    async def test_returns_404_when_repo_not_found(self, enc_key):
        pool = _make_pool(fetchrow_return=None)
        with patch("app.llm_config_router.db") as mock_db:
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.put(
                    "/api/repos/org/repo/llm-config",
                    json={"provider": "openai", "model": "gpt-4o"},
                )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/repos/{repo_id}/llm-config/test
# ---------------------------------------------------------------------------

class TestTestLLMConfig:
    @pytest.mark.asyncio
    async def test_returns_404_when_config_missing(self, enc_key):
        install_row = _install_row()
        pool = _make_pool(fetchrow_side_effect=[install_row, None])
        with patch("app.llm_config_router.db") as mock_db:
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/repos/org/repo/llm-config/test")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_probes_openai_provider_success(self, enc_key):
        api_key_enc = _encrypt("sk-ok", _FERNET_KEY)
        install_row = _install_row()
        cfg_row = _config_row(api_key_enc=api_key_enc)
        pool = _make_pool(fetchrow_side_effect=[install_row, cfg_row])

        with patch("app.llm_config_router.db") as mock_db, \
             patch("app.llm_config_router._probe_openai_compat", new=AsyncMock(return_value=None)):
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/repos/org/repo/llm-config/test")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_probes_ollama_provider_success(self, enc_key):
        install_row = _install_row()
        cfg_row = _Row({
            "id": _CONFIG_ID,
            "installation_id": _INSTALLATION_ID,
            "provider": "ollama",
            "model": "llama3",
            "base_url": "http://llm:11434",
            "api_key_enc": None,
            "created_at": _NOW,
            "updated_at": _NOW,
        })
        pool = _make_pool(fetchrow_side_effect=[install_row, cfg_row])

        with patch("app.llm_config_router.db") as mock_db, \
             patch("app.llm_config_router._probe_ollama_compat", new=AsyncMock(return_value=None)):
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/repos/org/repo/llm-config/test")
        assert resp.status_code == 200
        assert resp.json()["provider"] == "ollama"

    @pytest.mark.asyncio
    async def test_probe_failure_returns_502(self, enc_key):
        install_row = _install_row()
        cfg_row = _config_row(api_key_enc=None)
        pool = _make_pool(fetchrow_side_effect=[install_row, cfg_row])

        with patch("app.llm_config_router.db") as mock_db, \
             patch("app.llm_config_router._probe_openai_compat", new=AsyncMock(side_effect=Exception("conn refused"))):
            mock_db.get_pool.return_value = pool
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/repos/org/repo/llm-config/test")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Feature flag gating
# ---------------------------------------------------------------------------

class TestFeatureFlagGating:
    @pytest.mark.asyncio
    async def test_get_returns_403_when_flag_disabled(self, enc_key):
        with patch("app.llm_config_router._require_flag", new=AsyncMock(
            side_effect=__import__("fastapi").HTTPException(status_code=403, detail="disabled")
        )):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/repos/org/repo/llm-config")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_put_returns_403_when_flag_disabled(self, enc_key):
        with patch("app.llm_config_router._require_flag", new=AsyncMock(
            side_effect=__import__("fastapi").HTTPException(status_code=403, detail="disabled")
        )):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.put(
                    "/api/repos/org/repo/llm-config",
                    json={"provider": "openai", "model": "gpt-4o"},
                )
        assert resp.status_code == 403
