"""Unit tests for GET /admin/features, PUT /admin/features/{key}, DELETE /admin/features/{key}."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.features_router import _overrides, init_overrides, router

_app = FastAPI()
_app.include_router(router)


@pytest.fixture(autouse=True)
def reset_overrides():
    """Clear any in-memory overrides between tests."""
    _overrides.clear()
    yield
    _overrides.clear()


@pytest.mark.asyncio
async def test_get_features_returns_snapshot():
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
        r = await c.get("/admin/features")
    assert r.status_code == 200
    body = r.json()
    assert "flags" in body
    assert "catalog" in body
    assert "snapshot_at" in body
    assert isinstance(body["flags"], dict)
    assert len(body["catalog"]) > 0


@pytest.mark.asyncio
async def test_default_flags_structure():
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
        r = await c.get("/admin/features")
    flags = r.json()["flags"]
    assert flags.get("vcs.github") is True
    assert flags.get("vcs.gitlab") is True
    assert flags.get("vcs.bitbucket") is False
    assert flags.get("pipeline.diff") is True
    assert flags.get("pipeline.security_scan") is False
    assert flags.get("platform.multi_tenant") is False


@pytest.mark.asyncio
async def test_catalog_entry_fields():
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
        r = await c.get("/admin/features")
    catalog = r.json()["catalog"]
    entry = next(e for e in catalog if e["key"] == "vcs.github")
    assert entry["name"] == "GitHub"
    assert entry["category"] == "vcs"
    assert "description" in entry
    assert entry["enabled"] is True
    assert entry["default"] is True


@pytest.mark.asyncio
async def test_put_feature_toggle():
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
        r = await c.put("/admin/features/vcs.bitbucket", json={"enabled": True})
    assert r.status_code == 200
    assert r.json()["enabled"] is True
    assert _overrides["vcs.bitbucket"] is True


@pytest.mark.asyncio
async def test_put_feature_override_reflected_in_snapshot():
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
        await c.put("/admin/features/vcs.bitbucket", json={"enabled": True})
        r = await c.get("/admin/features")
    assert r.json()["flags"]["vcs.bitbucket"] is True


@pytest.mark.asyncio
async def test_put_unknown_flag_returns_404():
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
        r = await c.put("/admin/features/fake.flag", json={"enabled": True})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_env_override(monkeypatch):
    monkeypatch.setenv("VELLIC_FEATURE_VCS_BITBUCKET", "true")
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
        r = await c.get("/admin/features")
    assert r.json()["flags"]["vcs.bitbucket"] is True


@pytest.mark.asyncio
async def test_in_memory_override_wins_over_env(monkeypatch):
    monkeypatch.setenv("VELLIC_FEATURE_VCS_GITHUB", "false")
    _overrides["vcs.github"] = True
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
        r = await c.get("/admin/features")
    assert r.json()["flags"]["vcs.github"] is True


@pytest.mark.asyncio
async def test_delete_feature_removes_override():
    _overrides["vcs.bitbucket"] = True
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
        r = await c.delete("/admin/features/vcs.bitbucket")
    assert r.status_code == 200
    assert r.json()["removed"] is True
    assert "vcs.bitbucket" not in _overrides


@pytest.mark.asyncio
async def test_delete_unknown_flag_returns_404():
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
        r = await c.delete("/admin/features/fake.flag")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_restart_does_not_lose_overrides(monkeypatch):
    """init_overrides() restores cache from DB rows — simulates a service restart."""
    from app import db

    fake_row = MagicMock()
    fake_row.__getitem__ = lambda self, k: {"flag_key": "vcs.bitbucket", "value": True}[k]

    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[fake_row])

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr(db, "_pool", pool)

    _overrides.clear()
    await init_overrides()
    assert _overrides.get("vcs.bitbucket") is True
