import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.pipeline.feedback_poster import (
    GitHubClientError,
    RateLimitError,
    _build_inline_comments,
    _build_review_body,
    _check_rate_limit,
    post_github_review,
)
from app.pipeline.models import AnalysisResult, ReviewComment


# ---------------------------------------------------------------------------
# _build_review_body
# ---------------------------------------------------------------------------


def test_build_review_body_request_changes_when_high_confidence():
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 1, "fix this", 0.9, "security")],
        summary="Found issues.",
        generic_ratio=0.0,
    )
    body, event = _build_review_body(result)
    assert event == "REQUEST_CHANGES"
    assert "Found issues." in body
    assert "**Inline comments:** 1" in body
    assert "Request changes" in body


def test_build_review_body_comment_when_low_confidence():
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 1, "minor", 0.5, "style")],
        summary="Minor nit.",
        generic_ratio=0.5,
    )
    body, event = _build_review_body(result)
    assert event == "COMMENT"
    assert "No blocking issues" in body


def test_build_review_body_empty_comments():
    result = AnalysisResult(comments=[], summary="LGTM.", generic_ratio=0.0)
    body, event = _build_review_body(result)
    assert event == "COMMENT"
    assert "LGTM." in body
    assert "**Inline comments:** 0" in body
    assert "**Generic comment ratio:** 0%" in body


# ---------------------------------------------------------------------------
# _build_inline_comments
# ---------------------------------------------------------------------------


def test_build_inline_comments_maps_fields():
    comments = [ReviewComment("src/app.py", 42, "Use const", 0.9, "immutability")]
    result = _build_inline_comments(comments)
    assert len(result) == 1
    assert result[0]["path"] == "src/app.py"
    assert result[0]["line"] == 42
    assert result[0]["side"] == "RIGHT"
    assert "Use const" in result[0]["body"]
    assert "90%" in result[0]["body"]


def test_build_inline_comments_skips_zero_line():
    comments = [ReviewComment("app.py", 0, "bad", 0.8, "reason")]
    assert _build_inline_comments(comments) == []


def test_build_inline_comments_skips_empty_file():
    comments = [ReviewComment("", 10, "bad", 0.8, "reason")]
    assert _build_inline_comments(comments) == []


# ---------------------------------------------------------------------------
# _check_rate_limit
# ---------------------------------------------------------------------------


def test_check_rate_limit_ok():
    headers = httpx.Headers({"X-RateLimit-Remaining": "500"})
    _check_rate_limit(headers)  # should not raise


def test_check_rate_limit_triggers_below_threshold():
    headers = httpx.Headers({"X-RateLimit-Remaining": "50"})
    with pytest.raises(RateLimitError):
        _check_rate_limit(headers)


def test_check_rate_limit_at_boundary():
    headers = httpx.Headers({"X-RateLimit-Remaining": "99"})
    with pytest.raises(RateLimitError):
        _check_rate_limit(headers)


def test_check_rate_limit_missing_header_passes():
    headers = httpx.Headers({})
    _check_rate_limit(headers)  # defaults to 9999 — should not raise


# ---------------------------------------------------------------------------
# post_github_review — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_github_review_returns_review_id():
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 10, "fix this", 0.9, "reason")],
        summary="Issues found.",
        generic_ratio=0.0,
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = httpx.Headers({"X-RateLimit-Remaining": "4999"})
    mock_resp.json.return_value = {"id": 12345}

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=mock_resp)
        review_id = await post_github_review("acme/backend", 42, "abc123", result, token="tok")

    assert review_id == "12345"


@pytest.mark.asyncio
async def test_post_github_review_no_inline_comments():
    result = AnalysisResult(comments=[], summary="LGTM.", generic_ratio=0.0)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = httpx.Headers({"X-RateLimit-Remaining": "4999"})
    mock_resp.json.return_value = {"id": 99}

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=mock_resp)
        review_id = await post_github_review("acme/backend", 1, "sha1", result, token="tok")
        call_payload = instance.post.call_args[1]["json"]

    assert review_id == "99"
    assert "comments" not in call_payload


# ---------------------------------------------------------------------------
# post_github_review — rate limit guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_github_review_rate_limit_header_raises():
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = httpx.Headers({"X-RateLimit-Remaining": "50"})
    mock_resp.json.return_value = {"id": 1}

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=mock_resp)
        with pytest.raises(RateLimitError):
            await post_github_review("acme/backend", 1, "sha", result, token="tok")


@pytest.mark.asyncio
async def test_post_github_review_429_raises_rate_limit():
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = httpx.Headers({"X-RateLimit-Remaining": "9999"})

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=mock_resp)
        with pytest.raises(RateLimitError):
            await post_github_review("acme/backend", 1, "sha", result, token="tok")


# ---------------------------------------------------------------------------
# post_github_review — error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_github_review_5xx_raises_http_error():
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 503
    mock_resp.headers = httpx.Headers({"X-RateLimit-Remaining": "9999"})
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=mock_resp
    )

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=mock_resp)
        with pytest.raises(httpx.HTTPStatusError):
            await post_github_review("acme/backend", 1, "sha", result, token="tok")


@pytest.mark.asyncio
async def test_post_github_review_4xx_raises_client_error():
    result = AnalysisResult(comments=[], summary="ok", generic_ratio=0.0)
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.headers = httpx.Headers({"X-RateLimit-Remaining": "9999"})
    mock_resp.text = "Forbidden"

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=mock_resp)
        with pytest.raises(GitHubClientError):
            await post_github_review("acme/backend", 1, "sha", result, token="tok")


@pytest.mark.asyncio
async def test_post_github_review_422_retries_without_inline():
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 5, "fix", 0.9, "reason")],
        summary="Issues.",
        generic_ratio=0.0,
    )
    resp_422 = MagicMock()
    resp_422.status_code = 422
    resp_422.headers = httpx.Headers({"X-RateLimit-Remaining": "9999"})

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.headers = httpx.Headers({"X-RateLimit-Remaining": "9999"})
    resp_200.json.return_value = {"id": 777}

    with patch("app.pipeline.feedback_poster.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(side_effect=[resp_422, resp_200])
        review_id = await post_github_review("acme/backend", 1, "sha", result, token="tok")

    assert review_id == "777"
    assert instance.post.call_count == 2
    # Second call should not include inline comments
    second_payload = instance.post.call_args_list[1][1]["json"]
    assert "comments" not in second_payload


# ---------------------------------------------------------------------------
# post_feedback job — dedup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_feedback_skips_if_already_posted():
    from app.jobs import post_feedback

    pr_review_id = str(uuid.uuid4())
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value={
        "repo": "acme/backend",
        "pr_number": 42,
        "commit_sha": "abc123",
        "feedback": {"comments": [], "summary": "ok", "generic_ratio": 0.0},
        "github_review_id": "existing-review-id",
    })

    ctx = {"db_pool": mock_pool, "job_try": 1}
    with patch("app.jobs.post_github_review") as mock_post:
        await post_feedback(ctx, pr_review_id)
        mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_post_feedback_posts_and_updates_db():
    from app.jobs import post_feedback

    pr_review_id = str(uuid.uuid4())
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value={
        "repo": "acme/backend",
        "pr_number": 42,
        "commit_sha": "abc123",
        "feedback": {
            "comments": [
                {"file": "app.py", "line": 10, "body": "fix", "confidence": 0.9, "rationale": "r"}
            ],
            "summary": "Issues found.",
            "generic_ratio": 0.0,
        },
        "github_review_id": None,
    })
    mock_pool.execute = AsyncMock()

    ctx = {"db_pool": mock_pool, "job_try": 1}
    with patch("app.jobs.post_github_review", new=AsyncMock(return_value="gh-999")):
        await post_feedback(ctx, pr_review_id)

    mock_pool.execute.assert_called_once()
    call_args = mock_pool.execute.call_args[0]
    assert "github_review_id" in call_args[0]
    assert call_args[1] == "gh-999"
