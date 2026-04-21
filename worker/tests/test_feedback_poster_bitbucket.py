import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.pipeline.feedback_poster import (
    BitbucketClientError,
    RateLimitError,
    _build_bitbucket_summary_body,
    post_bitbucket_comment,
)
from app.pipeline.models import AnalysisResult, ReviewComment


# ---------------------------------------------------------------------------
# _build_bitbucket_summary_body
# ---------------------------------------------------------------------------


def test_build_bitbucket_summary_body_request_changes():
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 1, "fix this", 0.9, "security")],
        summary="Issues found.",
        generic_ratio=0.0,
    )
    body = _build_bitbucket_summary_body(result)
    assert "Issues found." in body
    assert "Request changes" in body
    assert "**Inline comments:** 1" in body


def test_build_bitbucket_summary_body_no_blocking():
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 1, "nit", 0.5, "style")],
        summary="Minor note.",
        generic_ratio=0.5,
    )
    body = _build_bitbucket_summary_body(result)
    assert "No blocking issues" in body
    assert "50%" in body


def test_build_bitbucket_summary_body_empty_comments():
    result = AnalysisResult(comments=[], summary="LGTM.", generic_ratio=0.0)
    body = _build_bitbucket_summary_body(result)
    assert "LGTM." in body
    assert "**Inline comments:** 0" in body


# ---------------------------------------------------------------------------
# post_bitbucket_comment — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_bitbucket_comment_returns_comment_id(monkeypatch):
    monkeypatch.setenv("BITBUCKET_TOKEN", "bb-oauth-token")
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 10, "fix this", 0.9, "reason")],
        summary="Issues found.",
        generic_ratio=0.0,
    )

    summary_resp = MagicMock(status_code=201)
    summary_resp.json.return_value = {"id": 999}
    inline_resp = MagicMock(status_code=201)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[summary_resp, inline_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient", return_value=mock_client):
        comment_id = await post_bitbucket_comment(
            repo="org/repo", pr_number=42, result=result
        )

    assert comment_id == "999"
    # First call: summary; second call: inline comment on app.py:10
    assert mock_client.post.call_count == 2
    first_call_json = mock_client.post.call_args_list[0][1]["json"]
    assert "content" in first_call_json
    assert "raw" in first_call_json["content"]

    second_call_json = mock_client.post.call_args_list[1][1]["json"]
    assert second_call_json["inline"]["to"] == 10
    assert second_call_json["inline"]["path"] == "app.py"


@pytest.mark.asyncio
async def test_post_bitbucket_comment_skips_zero_line_inline(monkeypatch):
    monkeypatch.setenv("BITBUCKET_TOKEN", "tok")
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 0, "general", 0.9, "reason")],
        summary="Summary.",
        generic_ratio=0.0,
    )

    summary_resp = MagicMock(status_code=201)
    summary_resp.json.return_value = {"id": 1}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=summary_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient", return_value=mock_client):
        comment_id = await post_bitbucket_comment(repo="org/repo", pr_number=1, result=result)

    assert comment_id == "1"
    # Only the summary call; zero-line comment is skipped
    assert mock_client.post.call_count == 1


# ---------------------------------------------------------------------------
# post_bitbucket_comment — auth header selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bearer_token_used_when_bitbucket_token_set(monkeypatch):
    monkeypatch.setenv("BITBUCKET_TOKEN", "my-oauth-token")
    monkeypatch.delenv("BITBUCKET_USERNAME", raising=False)
    monkeypatch.delenv("BITBUCKET_APP_PASSWORD", raising=False)

    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    summary_resp = MagicMock(status_code=201)
    summary_resp.json.return_value = {"id": 1}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=summary_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient", return_value=mock_client):
        await post_bitbucket_comment(repo="org/repo", pr_number=1, result=result)

    headers_used = mock_client.post.call_args_list[0][1]["headers"]
    assert headers_used["Authorization"] == "Bearer my-oauth-token"


@pytest.mark.asyncio
async def test_basic_auth_used_when_no_token(monkeypatch):
    monkeypatch.delenv("BITBUCKET_TOKEN", raising=False)
    monkeypatch.setenv("BITBUCKET_USERNAME", "user")
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "pass")

    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    summary_resp = MagicMock(status_code=201)
    summary_resp.json.return_value = {"id": 2}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=summary_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient", return_value=mock_client):
        await post_bitbucket_comment(repo="org/repo", pr_number=1, result=result)

    headers_used = mock_client.post.call_args_list[0][1]["headers"]
    expected = "Basic " + base64.b64encode(b"user:pass").decode()
    assert headers_used["Authorization"] == expected


# ---------------------------------------------------------------------------
# post_bitbucket_comment — error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_429_raises_rate_limit_error(monkeypatch):
    monkeypatch.setenv("BITBUCKET_TOKEN", "tok")
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)

    rate_limit_resp = MagicMock(status_code=429)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=rate_limit_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RateLimitError):
            await post_bitbucket_comment(repo="org/repo", pr_number=1, result=result)


@pytest.mark.asyncio
async def test_4xx_raises_bitbucket_client_error(monkeypatch):
    monkeypatch.setenv("BITBUCKET_TOKEN", "tok")
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)

    error_resp = MagicMock(status_code=403)
    error_resp.text = "Forbidden"

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=error_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(BitbucketClientError, match="403"):
            await post_bitbucket_comment(repo="org/repo", pr_number=1, result=result)


@pytest.mark.asyncio
async def test_inline_4xx_is_skipped_summary_returned(monkeypatch):
    monkeypatch.setenv("BITBUCKET_TOKEN", "tok")
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 5, "issue", 0.9, "reason")],
        summary="Issues.",
        generic_ratio=0.0,
    )

    summary_resp = MagicMock(status_code=201)
    summary_resp.json.return_value = {"id": 77}
    inline_err = MagicMock(status_code=422)
    inline_err.text = "invalid position"

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[summary_resp, inline_err])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient", return_value=mock_client):
        comment_id = await post_bitbucket_comment(repo="org/repo", pr_number=1, result=result)

    # Summary was posted; inline 422 was silently skipped
    assert comment_id == "77"


@pytest.mark.asyncio
async def test_inline_429_raises_rate_limit_error(monkeypatch):
    monkeypatch.setenv("BITBUCKET_TOKEN", "tok")
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 5, "issue", 0.9, "reason")],
        summary="Issues.",
        generic_ratio=0.0,
    )

    summary_resp = MagicMock(status_code=201)
    summary_resp.json.return_value = {"id": 1}
    inline_rate_limit = MagicMock(status_code=429)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[summary_resp, inline_rate_limit])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RateLimitError, match="inline"):
            await post_bitbucket_comment(repo="org/repo", pr_number=1, result=result)
