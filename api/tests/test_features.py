"""Tests for /api/features and /api/features/catalog endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture()
def mock_db_pool():
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=[])
    return pool


@pytest.fixture()
async def client(mock_db_pool):
    with (
        patch("app.features_router.db.get_pool", return_value=mock_db_pool),
        patch("app.features_router._cache", {}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


class TestCatalog:
    async def test_returns_200(self, client):
        resp = await client.get("/api/features/catalog")
        assert resp.status_code == 200

    async def test_contains_flags_list(self, client):
        resp = await client.get("/api/features/catalog")
        data = resp.json()
        assert "flags" in data
        assert isinstance(data["flags"], list)
        assert len(data["flags"]) > 0

    async def test_flag_has_required_fields(self, client):
        resp = await client.get("/api/features/catalog")
        flag = resp.json()["flags"][0]
        for field in ("key", "name", "category", "description", "default", "scope", "cost_impact", "requires", "tags"):
            assert field in flag, f"missing field: {field}"

    async def test_known_flag_present(self, client):
        resp = await client.get("/api/features/catalog")
        keys = {f["key"] for f in resp.json()["flags"]}
        assert "vcs.github" in keys
        assert "llm.openai" in keys
        assert "pipeline.llm_analysis" in keys


class TestFeaturesSnapshot:
    async def test_returns_200(self, client):
        resp = await client.get("/api/features")
        assert resp.status_code == 200

    async def test_response_shape(self, client):
        resp = await client.get("/api/features")
        data = resp.json()
        assert "flags" in data
        assert "cached_at" in data
        assert isinstance(data["flags"], dict)

    async def test_all_catalog_keys_present(self, client):
        from vellic_flags import CATALOG
        resp = await client.get("/api/features")
        keys = set(resp.json()["flags"].keys())
        for flag in CATALOG:
            assert flag.key in keys

    async def test_flag_values_are_bool(self, client):
        resp = await client.get("/api/features")
        for key, value in resp.json()["flags"].items():
            assert isinstance(value, bool), f"{key} is not bool"

    async def test_defaults_respected_without_overrides(self, client, mock_db_pool):
        mock_db_pool.fetch = AsyncMock(return_value=[])
        resp = await client.get("/api/features")
        flags = resp.json()["flags"]
        assert flags["vcs.github"] is True
        assert flags["vcs.bitbucket"] is False

    async def test_scope_params_accepted(self, client):
        resp = await client.get(
            "/api/features",
            params={"tenant_id": "acme", "repo_id": "acme/vellic", "user_id": "u-1"},
        )
        assert resp.status_code == 200

    async def test_db_override_applied(self, client, mock_db_pool):
        row = MagicMock()
        row.__getitem__ = lambda self, k: {
            "flag_key": "vcs.github",
            "scope": "global",
            "scope_id": "_global",
            "value": False,
        }[k]
        mock_db_pool.fetch = AsyncMock(return_value=[row])

        with patch("app.features_router._cache", {}):
            resp = await client.get("/api/features")
        assert resp.status_code == 200
        flags = resp.json()["flags"]
        assert flags["vcs.github"] is False

    async def test_caching_avoids_second_db_call(self, client, mock_db_pool):
        mock_db_pool.fetch = AsyncMock(return_value=[])
        with patch("app.features_router._cache", {}):
            await client.get("/api/features")
            await client.get("/api/features")
        assert mock_db_pool.fetch.call_count == 1
