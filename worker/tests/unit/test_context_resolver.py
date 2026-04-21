"""Unit tests for the prompt context-variable resolver (VEL-111)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.pipeline.models import DiffChunk, PRContext
from app.prompts.context_resolver import (
    _MAX_DIFF_CHARS,
    build_diff_text,
    build_prompt_context,
    extract_symbols_from_diff,
    fetch_prev_reviews,
    get_changed_files,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunk(filename: str, patch: str) -> DiffChunk:
    return DiffChunk(filename=filename, patch_lines=patch.splitlines())


def _pr_ctx(**kwargs) -> PRContext:
    defaults = dict(
        repo="acme/api",
        pr_number=42,
        commit_sha="abc123",
        title="Fix login",
        body="Fixes the auth flow",
        base_branch="main",
    )
    defaults.update(kwargs)
    return PRContext(**defaults)


# ---------------------------------------------------------------------------
# build_diff_text
# ---------------------------------------------------------------------------

def test_build_diff_text_single_chunk():
    chunk = _chunk("api/main.py", "@@ -1,3 +1,4 @@\n context\n+new line\n")
    result = build_diff_text([chunk])
    assert "api/main.py" in result
    assert "new line" in result
    assert "```diff" in result


def test_build_diff_text_empty():
    assert build_diff_text([]) == ""


def test_build_diff_text_multiple_chunks():
    chunks = [
        _chunk("a.py", "+def foo(): pass"),
        _chunk("b.py", "+class Bar: pass"),
    ]
    result = build_diff_text(chunks)
    assert "a.py" in result
    assert "b.py" in result


def test_build_diff_text_truncates_at_limit():
    big_patch = "+" + "x" * _MAX_DIFF_CHARS
    chunk = _chunk("huge.py", big_patch)
    result = build_diff_text([chunk])
    assert len(result) <= _MAX_DIFF_CHARS + 200  # header/footer overhead
    assert "truncated" in result


# ---------------------------------------------------------------------------
# extract_symbols_from_diff
# ---------------------------------------------------------------------------

def test_extract_symbols_python_function():
    chunk = _chunk("service.py", "+def authenticate(user, password):\n+    pass\n")
    result = extract_symbols_from_diff([chunk])
    assert "service.py: authenticate" in result


def test_extract_symbols_python_class():
    chunk = _chunk("models.py", "+class UserAccount:\n+    pass\n")
    result = extract_symbols_from_diff([chunk])
    assert "models.py: UserAccount" in result


def test_extract_symbols_js_function():
    chunk = _chunk("auth.js", "+function login(email) {\n+  return true;\n}")
    result = extract_symbols_from_diff([chunk])
    assert "auth.js: login" in result


def test_extract_symbols_go_function():
    chunk = _chunk("handler.go", "+func HandleAuth(w http.ResponseWriter, r *http.Request) {\n}")
    result = extract_symbols_from_diff([chunk])
    assert "handler.go: HandleAuth" in result


def test_extract_symbols_rust_fn():
    chunk = _chunk("lib.rs", "+pub fn verify_token(token: &str) -> bool {\n    true\n}")
    result = extract_symbols_from_diff([chunk])
    assert "lib.rs: verify_token" in result


def test_extract_symbols_dedup_per_file():
    patch = "+def foo():\n+    pass\n+def foo():\n+    return 1\n"
    chunk = _chunk("dupe.py", patch)
    result = extract_symbols_from_diff([chunk])
    assert result.count("dupe.py: foo") == 1


def test_extract_symbols_removed_lines_ignored():
    chunk = _chunk("old.py", "-def removed_func():\n-    pass\n")
    result = extract_symbols_from_diff([chunk])
    assert "removed_func" not in result


def test_extract_symbols_empty_diff():
    assert extract_symbols_from_diff([]) == ""


def test_extract_symbols_no_match():
    chunk = _chunk("readme.md", "+ Some documentation text.\n")
    result = extract_symbols_from_diff([chunk])
    assert result == ""


# ---------------------------------------------------------------------------
# get_changed_files
# ---------------------------------------------------------------------------

def test_get_changed_files_deduplicates():
    chunks = [
        _chunk("api/main.py", "+line1"),
        _chunk("api/main.py", "+line2"),
        _chunk("api/auth.py", "+line3"),
    ]
    files = get_changed_files(chunks)
    assert files == ["api/main.py", "api/auth.py"]


def test_get_changed_files_preserves_order():
    chunks = [_chunk(f"file{i}.py", "+x") for i in range(5)]
    files = get_changed_files(chunks)
    assert files == [f"file{i}.py" for i in range(5)]


def test_get_changed_files_empty():
    assert get_changed_files([]) == []


# ---------------------------------------------------------------------------
# build_prompt_context
# ---------------------------------------------------------------------------

def test_build_prompt_context_basic():
    ctx = _pr_ctx()
    chunks = [_chunk("api.py", "+def new_endpoint():\n+    pass")]
    result = build_prompt_context(ctx, chunks, labels=["bug", "auth"])

    assert result.repo == "acme/api"
    assert result.pr_title == "Fix login"
    assert result.pr_body == "Fixes the auth flow"
    assert result.base_branch == "main"
    assert result.labels == ["bug", "auth"]
    assert "api.py" in result.diff
    assert "api.py: new_endpoint" in result.symbols
    assert "api.py" in result.changed_files


def test_build_prompt_context_prev_reviews():
    ctx = _pr_ctx()
    prev = ["First review summary", "Second review summary"]
    result = build_prompt_context(ctx, [], prev_reviews=prev)
    assert result.prev_reviews == prev


def test_build_prompt_context_coverage_passthrough():
    ctx = _pr_ctx()
    result = build_prompt_context(ctx, [], coverage="Stmts: 82%")
    assert result.coverage == "Stmts: 82%"


def test_build_prompt_context_extra_overrides():
    ctx = _pr_ctx()
    result = build_prompt_context(ctx, [], extra={"custom_key": "custom_val"})
    d = result.as_dict()
    assert d["custom_key"] == "custom_val"


def test_build_prompt_context_labels_none():
    ctx = _pr_ctx()
    result = build_prompt_context(ctx, [], labels=None)
    assert result.labels == []


def test_build_prompt_context_as_dict_all_keys():
    ctx = _pr_ctx()
    chunks = [_chunk("x.py", "+def f(): pass")]
    result = build_prompt_context(ctx, chunks, labels=["refactor"])
    d = result.as_dict()
    for key in ("diff", "symbols", "coverage", "prev_reviews", "pr_title",
                "pr_body", "repo", "base_branch", "changed_files", "labels"):
        assert key in d, f"missing key: {key}"
    assert d["labels"] == "refactor"
    assert d["changed_files"] == "x.py"


# ---------------------------------------------------------------------------
# fetch_prev_reviews (async, uses mocked DB pool)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_prev_reviews_returns_summaries():
    mock_row = {"summary": "LGTM overall"}
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[mock_row])
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    ))

    result = await fetch_prev_reviews(mock_pool, "acme/api", 42)
    assert result == ["LGTM overall"]


@pytest.mark.asyncio
async def test_fetch_prev_reviews_empty_when_no_rows():
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    ))

    result = await fetch_prev_reviews(mock_pool, "acme/api", 99)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_prev_reviews_graceful_on_db_error():
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(side_effect=RuntimeError("db down")),
        __aexit__=AsyncMock(return_value=None),
    ))

    result = await fetch_prev_reviews(mock_pool, "acme/api", 1)
    assert result == []
