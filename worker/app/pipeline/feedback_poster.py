import logging
import os
from typing import Any

import httpx

from .models import AnalysisResult, ReviewComment

logger = logging.getLogger("worker.pipeline.feedback_poster")

_GITHUB_API_BASE = "https://api.github.com"
_RATE_LIMIT_THRESHOLD = 100
_HIGH_CONFIDENCE_THRESHOLD = 0.8


class RateLimitError(Exception):
    """Raised when GitHub rate limit remaining drops below threshold or 429 received."""


class GitHubClientError(Exception):
    """Terminal 4xx error from GitHub (not 422 or 429)."""


def _build_review_body(result: AnalysisResult) -> tuple[str, str]:
    """Return (body_text, event_string) for the GitHub review."""
    high_conf = sum(1 for c in result.comments if c.confidence >= _HIGH_CONFIDENCE_THRESHOLD)
    event = "REQUEST_CHANGES" if high_conf > 0 else "COMMENT"

    rec_text = "Request changes" if event == "REQUEST_CHANGES" else "No blocking issues found"
    body = "\n".join([
        result.summary,
        "",
        f"**Inline comments:** {len(result.comments)}",
        f"**Generic comment ratio:** {result.generic_ratio:.0%}",
        f"**Recommendation:** {rec_text}",
    ])
    return body, event


def _build_inline_comments(comments: list[ReviewComment]) -> list[dict[str, Any]]:
    return [
        {
            "path": c.file,
            "line": c.line,
            "side": "RIGHT",
            "body": f"{c.body}\n\n*Confidence: {c.confidence:.0%} — {c.rationale}*",
        }
        for c in comments
        if c.line > 0 and c.file
    ]


def _check_rate_limit(headers: httpx.Headers) -> None:
    remaining = int(headers.get("X-RateLimit-Remaining", "9999"))
    if remaining < _RATE_LIMIT_THRESHOLD:
        logger.warning("GitHub rate limit low: remaining=%d", remaining)
        raise RateLimitError(f"X-RateLimit-Remaining={remaining}")


async def post_github_review(
    repo: str,
    pr_number: int,
    commit_sha: str,
    result: AnalysisResult,
    token: str | None = None,
) -> str:
    """Post analysis as a GitHub PR review. Returns the GitHub review ID as a string."""
    resolved_token = token or os.getenv("GITHUB_TOKEN", "")
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"

    body, event = _build_review_body(result)
    inline = _build_inline_comments(result.comments)

    payload: dict[str, Any] = {
        "commit_id": commit_sha,
        "body": body,
        "event": event,
    }
    if inline:
        payload["comments"] = inline

    url = f"{_GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}/reviews"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

    _check_rate_limit(resp.headers)

    if resp.status_code == 422 and inline:
        # Some line numbers may not exist in the diff; fall back to body-only review
        logger.warning(
            "422 with inline comments for %s#%d — retrying body-only", repo, pr_number
        )
        payload_no_inline = {k: v for k, v in payload.items() if k != "comments"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload_no_inline, headers=headers)
        _check_rate_limit(resp.headers)

    if resp.status_code == 429:
        raise RateLimitError("429 from GitHub")

    if resp.status_code >= 500:
        resp.raise_for_status()

    if resp.status_code >= 400:
        raise GitHubClientError(f"GitHub {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    return str(data["id"])
