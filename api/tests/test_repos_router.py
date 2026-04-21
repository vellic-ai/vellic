"""Tests for GET/PUT /api/repos/{repo_id}/config."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

_NOW = datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc)

_VALID_YAML = """\
rules:
  - id: no_print
    pattern: "print("
    languages: [python]
    severity: warning
ignore:
  - "tests/**"
severity_threshold: warning
"""


@pytest.fixture()
def mock_pool():
    pool = MagicMock()
    pool.fetchrow = AsyncMock()
    return pool


@pytest.fixture(autouse=True)
def patch_db(mock_pool):
    with patch("app.repos_router.db") as mock_db:
        mock_db.get_pool.return_value = mock_pool
        yield mock_db, mock_pool


# ---------------------------------------------------------------------------
# GET /api/repos/{repo_id}/config
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_config_returns_default_when_not_found(patch_db):
    _, mock_pool = patch_db
    mock_pool.fetchrow = AsyncMock(return_value=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/repos/org%2Frepo/config")

    assert resp.status_code == 200
    data = resp.json()
    assert data["repo_id"] == "org/repo"
    assert data["rules_yaml"] == ""


@pytest.mark.asyncio
async def test_get_config_returns_stored_yaml(patch_db):
    _, mock_pool = patch_db
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "repo_id": "org/repo",
        "rules_yaml": _VALID_YAML,
        "updated_at": _NOW,
    }[key]
    mock_pool.fetchrow = AsyncMock(return_value=row)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/repos/org%2Frepo/config")

    assert resp.status_code == 200
    data = resp.json()
    assert data["repo_id"] == "org/repo"
    assert "no_print" in data["rules_yaml"]


# ---------------------------------------------------------------------------
# PUT /api/repos/{repo_id}/config
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_put_config_stores_valid_yaml(patch_db):
    _, mock_pool = patch_db
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "repo_id": "org/repo",
        "rules_yaml": _VALID_YAML,
        "updated_at": _NOW,
    }[key]
    mock_pool.fetchrow = AsyncMock(return_value=row)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put(
            "/api/repos/org%2Frepo/config",
            json={"rules_yaml": _VALID_YAML},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["repo_id"] == "org/repo"


@pytest.mark.asyncio
async def test_put_config_empty_yaml_is_valid(patch_db):
    _, mock_pool = patch_db
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "repo_id": "org/repo",
        "rules_yaml": "",
        "updated_at": _NOW,
    }[key]
    mock_pool.fetchrow = AsyncMock(return_value=row)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put("/api/repos/org%2Frepo/config", json={"rules_yaml": ""})

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_put_config_invalid_yaml_returns_422(patch_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put(
            "/api/repos/org%2Frepo/config",
            json={"rules_yaml": "{ invalid: yaml: ["},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_config_rule_missing_id_returns_422(patch_db):
    bad_yaml = "rules:\n  - pattern: foo\n"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put("/api/repos/org%2Frepo/config", json={"rules_yaml": bad_yaml})

    assert resp.status_code == 422
    assert "id" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_put_config_invalid_severity_returns_422(patch_db):
    bad_yaml = "rules:\n  - id: r1\n    pattern: foo\n    severity: critical\n"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put("/api/repos/org%2Frepo/config", json={"rules_yaml": bad_yaml})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_config_invalid_threshold_returns_422(patch_db):
    bad_yaml = "rules: []\nseverity_threshold: critical\n"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put("/api/repos/org%2Frepo/config", json={"rules_yaml": bad_yaml})

    assert resp.status_code == 422
