"""Unit tests for worker/app/prompts/repo_loader.py (VEL-115)."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.prompts.models import PromptFile
from app.prompts.repo_loader import load_repo_prompts, load_repo_prompts_sync

_VALID_PROMPT = textwrap.dedent("""\
    ---
    scope: []
    triggers: []
    priority: 0
    ---
    Review this diff carefully.
""")

_VALID_PROMPT_B = textwrap.dedent("""\
    ---
    scope: ["api/**"]
    triggers: []
    priority: 5
    ---
    Focus on API surface.
""")


def _make_repo_dir(tmp_path: Path, files: dict[str, str]) -> Path:
    prompts_dir = tmp_path / ".vellic" / "prompts"
    prompts_dir.mkdir(parents=True)
    for name, content in files.items():
        (prompts_dir / f"{name}.md").write_text(content)
    return tmp_path


class _FakeConn:
    """Minimal asyncpg connection stub."""
    def __init__(self, override_rows: list[dict]) -> None:
        self._rows = override_rows

    async def fetch(self, query: str, *args) -> list[dict]:
        return self._rows


@pytest.mark.asyncio
async def test_no_overrides_returns_repo_files(tmp_path: Path) -> None:
    repo_root = _make_repo_dir(tmp_path, {"my-review": _VALID_PROMPT})
    conn = _FakeConn([])
    result = await load_repo_prompts(str(repo_root), "org/repo", conn)
    assert len(result) == 1
    assert result[0].name == "my-review"
    assert result[0].source == "repo"


@pytest.mark.asyncio
async def test_db_override_replaces_repo_file(tmp_path: Path) -> None:
    repo_root = _make_repo_dir(tmp_path, {"my-review": _VALID_PROMPT})
    override_body = _VALID_PROMPT_B
    conn = _FakeConn([{"path": "my-review", "body": override_body, "updated_at": None}])
    result = await load_repo_prompts(str(repo_root), "org/repo", conn)
    assert len(result) == 1
    assert result[0].source == "db"
    assert result[0].frontmatter.priority == 5


@pytest.mark.asyncio
async def test_db_only_override_is_appended(tmp_path: Path) -> None:
    repo_root = _make_repo_dir(tmp_path, {"my-review": _VALID_PROMPT})
    conn = _FakeConn([{"path": "extra-review", "body": _VALID_PROMPT_B, "updated_at": None}])
    result = await load_repo_prompts(str(repo_root), "org/repo", conn)
    names = {p.name for p in result}
    assert "my-review" in names
    assert "extra-review" in names
    assert len(result) == 2


@pytest.mark.asyncio
async def test_malformed_db_override_is_skipped(tmp_path: Path) -> None:
    repo_root = _make_repo_dir(tmp_path, {"my-review": _VALID_PROMPT})
    conn = _FakeConn([{"path": "bad", "body": "not valid frontmatter", "updated_at": None}])
    result = await load_repo_prompts(str(repo_root), "org/repo", conn)
    names = {p.name for p in result}
    assert "bad" not in names
    assert "my-review" in names


@pytest.mark.asyncio
async def test_empty_repo_dir_with_overrides(tmp_path: Path) -> None:
    # No .vellic/prompts dir at all
    conn = _FakeConn([{"path": "db-only", "body": _VALID_PROMPT_B, "updated_at": None}])
    result = await load_repo_prompts(str(tmp_path), "org/repo", conn)
    assert len(result) == 1
    assert result[0].name == "db-only"
    assert result[0].source == "db"


def test_sync_loader_returns_repo_files(tmp_path: Path) -> None:
    repo_root = _make_repo_dir(tmp_path, {"my-review": _VALID_PROMPT})
    result = load_repo_prompts_sync(str(repo_root))
    assert len(result) == 1
    assert result[0].name == "my-review"


def test_sync_loader_empty_dir(tmp_path: Path) -> None:
    result = load_repo_prompts_sync(str(tmp_path))
    assert result == []
