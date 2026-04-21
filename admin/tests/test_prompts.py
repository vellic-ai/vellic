"""Tests for /admin/prompts endpoints (VEL-114)."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.prompts_router import _require_prompt_dsl, router

_app = FastAPI()
_app.include_router(router)
# Override the feature-flag guard so unit tests run without the flag enabled.
_app.dependency_overrides[_require_prompt_dsl] = lambda: None

_REVIEW_ID = str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pool(fetchrow_result=None):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    pool = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool, conn


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=_app), base_url="http://test")


# ---------------------------------------------------------------------------
# GET /admin/prompts
# ---------------------------------------------------------------------------


async def test_list_prompts_returns_presets(client, tmp_path):
    preset = tmp_path / "review.md"
    preset.write_text(
        "---\npriority: 5\n---\nReview {{ diff }} carefully.\n", encoding="utf-8"
    )
    with patch("app.prompts_router.load_all_presets") as mock_load:
        from app.prompts.models import PromptFile, PromptFrontmatter

        mock_load.return_value = [
            PromptFile(
                name="review",
                path=str(preset),
                frontmatter=PromptFrontmatter(priority=5),
                body="Review {{ diff }} carefully.",
                source="preset",
            )
        ]
        async with client as c:
            r = await c.get("/admin/prompts")

    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["name"] == "review"
    assert item["source"] == "preset"
    assert item["frontmatter"]["priority"] == 5
    assert "{{ diff }}" in item["body"]


async def test_list_prompts_uses_real_presets(client):
    # Sanity check: the actual preset files can be parsed.
    async with client as c:
        r = await c.get("/admin/prompts")
    assert r.status_code == 200
    items = r.json()["items"]
    # At least some presets should exist (dev monorepo has worker/app/prompts/presets/)
    # If presets dir is missing we still get 200 with empty list.
    assert isinstance(items, list)


# ---------------------------------------------------------------------------
# GET /admin/prompts/{name}
# ---------------------------------------------------------------------------


async def test_get_prompt_found(client):
    from app.prompts.models import PromptFile, PromptFrontmatter

    fake = PromptFile(
        name="secure-review",
        path="/fake/secure-review.md",
        frontmatter=PromptFrontmatter(priority=10),
        body="Check for vulnerabilities.",
        source="preset",
    )
    with patch("app.prompts_router.load_preset", return_value=fake):
        async with client as c:
            r = await c.get("/admin/prompts/secure-review")

    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "secure-review"
    assert data["source"] == "preset"


async def test_get_prompt_not_found(client):
    with patch("app.prompts_router.load_preset", side_effect=ValueError("not found")):
        async with client as c:
            r = await c.get("/admin/prompts/nonexistent")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /admin/prompts/resolve
# ---------------------------------------------------------------------------


async def test_resolve_not_found(client):
    pool, conn = _make_pool(fetchrow_result=None)
    with patch("app.prompts_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(f"/admin/prompts/resolve?pr={_REVIEW_ID}")
    assert r.status_code == 404


async def test_resolve_returns_rendered_prompt(client):
    from app.prompts.models import PromptFile, PromptFrontmatter

    row = {
        "repo": "acme/api",
        "pr_number": 42,
        "commit_sha": "abc123",
        "payload": {
            "pull_request": {
                "title": "Add feature",
                "body": "Some description",
                "base": {"ref": "main"},
                "labels": [],
            }
        },
    }
    pool, _ = _make_pool(fetchrow_result=row)
    fake_preset = PromptFile(
        name="style-review",
        path="",
        frontmatter=PromptFrontmatter(priority=0),
        body="Review PR: {{ pr_title }} on {{ repo }}",
        source="preset",
    )

    with (
        patch("app.prompts_router.db.get_pool", return_value=pool),
        patch("app.prompts_router.load_all_presets", return_value=[fake_preset]),
    ):
        async with client as c:
            r = await c.post(f"/admin/prompts/resolve?pr={_REVIEW_ID}")

    assert r.status_code == 200
    data = r.json()
    assert "body" in data
    assert "sources" in data
    assert "Add feature" in data["body"]
    assert "acme/api" in data["body"]
    assert "style-review" in data["sources"]


# ---------------------------------------------------------------------------
# POST /admin/prompts/dry-run
# ---------------------------------------------------------------------------


async def test_dry_run_not_found(client):
    pool, conn = _make_pool(fetchrow_result=None)
    with patch("app.prompts_router.db.get_pool", return_value=pool):
        async with client as c:
            r = await c.post(
                "/admin/prompts/dry-run",
                json={"pr_review_id": _REVIEW_ID},
            )
    assert r.status_code == 404


async def test_dry_run_returns_analysis(client):
    from app.prompts.models import PromptFile, PromptFrontmatter

    row = {
        "repo": "acme/api",
        "pr_number": 7,
        "commit_sha": "def456",
        "payload": {
            "pull_request": {
                "title": "Fix bug",
                "body": "",
                "base": {"ref": "main"},
                "labels": [],
            }
        },
    }
    llm_row = {
        "provider": "ollama",
        "base_url": "http://ollama:11434",
        "model": "llama3.1:8b",
        "api_key": None,
    }
    fake_preset = PromptFile(
        name="test-review",
        path="",
        frontmatter=PromptFrontmatter(priority=0),
        body="Analyze {{ pr_title }}.",
        source="preset",
    )
    fake_analysis = {
        "comments": [],
        "summary": "Looks good.",
        "generic_ratio": 0.0,
    }

    pool, conn = _make_pool()
    # fetchrow called twice: once for pr_row, once for llm_settings
    conn.fetchrow = AsyncMock(side_effect=[row, llm_row])

    with (
        patch("app.prompts_router.db.get_pool", return_value=pool),
        patch("app.prompts_router.load_all_presets", return_value=[fake_preset]),
        patch("app.prompts_router._fetch_diff_chunks", return_value=[]),
        patch("app.prompts_router._call_llm", return_value=fake_analysis),
    ):
        async with client as c:
            r = await c.post(
                "/admin/prompts/dry-run",
                json={"pr_review_id": _REVIEW_ID},
            )

    assert r.status_code == 200
    data = r.json()
    assert "rendered_prompt" in data
    assert "sources" in data
    assert "analysis" in data
    assert data["analysis"]["summary"] == "Looks good."
    assert "Fix bug" in data["rendered_prompt"]


async def test_dry_run_no_llm_config(client):
    row = {
        "repo": "acme/api",
        "pr_number": 7,
        "commit_sha": "def456",
        "payload": {"pull_request": {"title": "x", "body": "", "base": {"ref": "main"}, "labels": []}},
    }
    pool, conn = _make_pool()
    conn.fetchrow = AsyncMock(side_effect=[row, None])  # no llm_settings

    with (
        patch("app.prompts_router.db.get_pool", return_value=pool),
        patch("app.prompts_router.load_all_presets", return_value=[]),
        patch("app.prompts_router._fetch_diff_chunks", return_value=[]),
    ):
        async with client as c:
            r = await c.post(
                "/admin/prompts/dry-run",
                json={"pr_review_id": _REVIEW_ID},
            )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Flag-gating tests (VEL-116): all endpoints return 404 when DSL flag is off
# ---------------------------------------------------------------------------


async def test_prompts_endpoints_return_404_when_flag_disabled():
    """Without the dependency override, all /admin/prompts endpoints are gated."""
    gated_app = FastAPI()
    gated_app.include_router(router)
    # Note: NO dependency_overrides — flag defaults to False

    async with AsyncClient(transport=ASGITransport(app=gated_app), base_url="http://test") as c:
        r_list = await c.get("/admin/prompts")
        r_get = await c.get("/admin/prompts/secure-review")
        r_resolve = await c.post(f"/admin/prompts/resolve?pr={_REVIEW_ID}")
        r_dry_run = await c.post("/admin/prompts/dry-run", json={"pr_review_id": _REVIEW_ID})

    assert r_list.status_code == 404
    assert r_get.status_code == 404
    assert r_resolve.status_code == 404
    assert r_dry_run.status_code == 404
