from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.pipeline.feedback_poster import (
    GitLabClientError,
    RateLimitError,
    _build_gitlab_note_body,
    post_gitlab_discussion,
)
from app.pipeline.models import AnalysisResult, ReviewComment


# ---------------------------------------------------------------------------
# _build_gitlab_note_body
# ---------------------------------------------------------------------------


def test_build_gitlab_note_body_request_changes():
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 1, "fix this", 0.9, "security")],
        summary="Issues found.",
        generic_ratio=0.0,
    )
    body = _build_gitlab_note_body(result)
    assert "Issues found." in body
    assert "Request changes" in body
    assert "**Inline comments:** 1" in body


def test_build_gitlab_note_body_no_blocking():
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 1, "nit", 0.5, "style")],
        summary="Minor note.",
        generic_ratio=0.5,
    )
    body = _build_gitlab_note_body(result)
    assert "No blocking issues" in body
    assert "50%" in body


def test_build_gitlab_note_body_empty_comments():
    result = AnalysisResult(comments=[], summary="LGTM.", generic_ratio=0.0)
    body = _build_gitlab_note_body(result)
    assert "LGTM." in body
    assert "**Inline comments:** 0" in body


# ---------------------------------------------------------------------------
# post_gitlab_discussion — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_gitlab_discussion_returns_note_id():
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 10, "fix this", 0.9, "reason")],
        summary="Issues found.",
        generic_ratio=0.0,
    )
    note_resp = MagicMock()
    note_resp.status_code = 201
    note_resp.json.return_value = {"id": 777}

    inline_resp = MagicMock()
    inline_resp.status_code = 201

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(side_effect=[note_resp, inline_resp])
        note_id = await post_gitlab_discussion("group/repo", 1, "sha1", result, token="tok")

    assert note_id == "777"


@pytest.mark.asyncio
async def test_post_gitlab_discussion_no_inline_skips_discussions():
    result = AnalysisResult(comments=[], summary="LGTM.", generic_ratio=0.0)
    note_resp = MagicMock()
    note_resp.status_code = 200
    note_resp.json.return_value = {"id": 99}

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=note_resp)
        note_id = await post_gitlab_discussion("group/repo", 1, "sha1", result, token="tok")

    assert note_id == "99"
    assert instance.post.call_count == 1  # only summary note


@pytest.mark.asyncio
async def test_post_gitlab_discussion_skips_zero_line_comment():
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 0, "body", 0.9, "r")],
        summary="ok",
        generic_ratio=0.0,
    )
    note_resp = MagicMock()
    note_resp.status_code = 200
    note_resp.json.return_value = {"id": 1}

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=note_resp)
        await post_gitlab_discussion("group/repo", 1, "sha", result, token="tok")

    assert instance.post.call_count == 1  # zero-line comment skipped


# ---------------------------------------------------------------------------
# post_gitlab_discussion — error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_gitlab_discussion_429_raises_rate_limit():
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    resp = MagicMock()
    resp.status_code = 429

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=resp)
        with pytest.raises(RateLimitError):
            await post_gitlab_discussion("group/repo", 1, "sha", result, token="tok")


@pytest.mark.asyncio
async def test_post_gitlab_discussion_4xx_raises_client_error():
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    resp = MagicMock()
    resp.status_code = 403
    resp.text = "Forbidden"

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=resp)
        with pytest.raises(GitLabClientError):
            await post_gitlab_discussion("group/repo", 1, "sha", result, token="tok")


@pytest.mark.asyncio
async def test_post_gitlab_discussion_5xx_raises_http_error():
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 503
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=resp
    )

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=resp)
        with pytest.raises(httpx.HTTPStatusError):
            await post_gitlab_discussion("group/repo", 1, "sha", result, token="tok")


@pytest.mark.asyncio
async def test_post_gitlab_discussion_inline_422_is_logged_not_raised():
    """A 422 on an inline comment position should not prevent the summary from returning."""
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 5, "fix", 0.9, "reason")],
        summary="Issues.",
        generic_ratio=0.0,
    )
    note_resp = MagicMock()
    note_resp.status_code = 201
    note_resp.json.return_value = {"id": 42}

    inline_resp = MagicMock()
    inline_resp.status_code = 422
    inline_resp.text = "invalid line"

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(side_effect=[note_resp, inline_resp])
        note_id = await post_gitlab_discussion("group/repo", 1, "sha", result, token="tok")

    assert note_id == "42"  # summary still returned
    assert instance.post.call_count == 2


@pytest.mark.asyncio
async def test_post_gitlab_discussion_url_encodes_repo_path():
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"id": 1}

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=resp)
        await post_gitlab_discussion("my-group/my-repo", 3, "sha", result, token="tok")

    called_url = instance.post.call_args_list[0][0][0]
    assert "my-group%2Fmy-repo" in called_url
