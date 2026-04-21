import base64
import logging
import os
from typing import Any
from urllib.parse import quote

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

    if resp.status_code == 422 and inline:
        # Some line numbers may not exist in the diff; fall back to body-only review
        logger.warning(
            "422 with inline comments for %s#%d — retrying body-only", repo, pr_number
        )
        payload_no_inline = {k: v for k, v in payload.items() if k != "comments"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload_no_inline, headers=headers)

    if resp.status_code == 429:
        raise RateLimitError("429 from GitHub")

    if resp.status_code >= 500:
        resp.raise_for_status()

    if resp.status_code >= 400:
        raise GitHubClientError(f"GitHub {resp.status_code}: {resp.text[:300]}")

    _check_rate_limit(resp.headers)
    data = resp.json()
    return str(data["id"])


# ---------------------------------------------------------------------------
# GitLab
# ---------------------------------------------------------------------------


class GitLabClientError(Exception):
    """Terminal 4xx error from GitLab (not 429)."""


def _gitlab_api_base() -> str:
    return os.getenv("GITLAB_BASE_URL", "https://gitlab.com").rstrip("/") + "/api/v4"


def _build_gitlab_note_body(result: AnalysisResult) -> str:
    high_conf = sum(1 for c in result.comments if c.confidence >= _HIGH_CONFIDENCE_THRESHOLD)
    rec_text = "Request changes" if high_conf > 0 else "No blocking issues found"
    return "\n".join([
        result.summary,
        "",
        f"**Inline comments:** {len(result.comments)}",
        f"**Generic comment ratio:** {result.generic_ratio:.0%}",
        f"**Recommendation:** {rec_text}",
    ])


async def post_gitlab_discussion(
    repo: str,
    mr_iid: int,
    commit_sha: str,
    result: AnalysisResult,
    token: str | None = None,
) -> str:
    """Post analysis as a GitLab MR discussion note + inline comments.

    Returns the ID of the summary note as a string.
    """
    resolved_token = token or os.getenv("GITLAB_TOKEN", "")
    encoded_repo = quote(repo, safe="")
    base = _gitlab_api_base()
    notes_url = f"{base}/projects/{encoded_repo}/merge_requests/{mr_iid}/notes"
    discussions_url = f"{base}/projects/{encoded_repo}/merge_requests/{mr_iid}/discussions"

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if resolved_token:
        headers["PRIVATE-TOKEN"] = resolved_token

    summary_body = _build_gitlab_note_body(result)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(notes_url, json={"body": summary_body}, headers=headers)

    if resp.status_code == 429:
        raise RateLimitError("429 from GitLab")
    if resp.status_code >= 500:
        resp.raise_for_status()
    if resp.status_code >= 400:
        raise GitLabClientError(f"GitLab {resp.status_code}: {resp.text[:300]}")

    note_id = str(resp.json()["id"])

    # Post each high-confidence inline comment as a positioned discussion.
    # A 422 on a specific line position is silently skipped to not block the summary.
    async with httpx.AsyncClient(timeout=30.0) as client:
        for comment in result.comments:
            if comment.line <= 0 or not comment.file:
                continue
            body = f"{comment.body}\n\n*Confidence: {comment.confidence:.0%} — {comment.rationale}*"
            discussion_payload: dict[str, Any] = {
                "body": body,
                "position": {
                    "base_sha": commit_sha,
                    "start_sha": commit_sha,
                    "head_sha": commit_sha,
                    "position_type": "text",
                    "new_path": comment.file,
                    "new_line": comment.line,
                },
            }
            inline_resp = await client.post(
                discussions_url, json=discussion_payload, headers=headers
            )
            if inline_resp.status_code == 429:
                raise RateLimitError("429 from GitLab (inline comment)")
            if inline_resp.status_code >= 500:
                inline_resp.raise_for_status()
            if inline_resp.status_code >= 400:
                logger.warning(
                    "skipping inline comment on %s:%d — GitLab %d: %s",
                    comment.file,
                    comment.line,
                    inline_resp.status_code,
                    inline_resp.text[:200],
                )

    return note_id


# ---------------------------------------------------------------------------
# Bitbucket Cloud
# ---------------------------------------------------------------------------

_BITBUCKET_API_BASE = "https://api.bitbucket.org/2.0"


class BitbucketClientError(Exception):
    """Terminal 4xx error from Bitbucket (not 429)."""


def _bitbucket_auth_headers(token: str | None) -> dict[str, str]:
    """Return Authorization headers for Bitbucket API calls.

    Prefers OAuth Bearer token (BITBUCKET_TOKEN); falls back to app-password Basic auth.
    """
    bb_token = token or os.getenv("BITBUCKET_TOKEN", "")
    bb_user = os.getenv("BITBUCKET_USERNAME", "")
    bb_pass = os.getenv("BITBUCKET_APP_PASSWORD", "")

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if bb_token:
        headers["Authorization"] = f"Bearer {bb_token}"
    elif bb_user and bb_pass:
        credentials = base64.b64encode(f"{bb_user}:{bb_pass}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

    return headers


def _build_bitbucket_summary_body(result: AnalysisResult) -> str:
    high_conf = sum(1 for c in result.comments if c.confidence >= _HIGH_CONFIDENCE_THRESHOLD)
    rec_text = "Request changes" if high_conf > 0 else "No blocking issues found"
    return "\n".join([
        result.summary,
        "",
        f"**Inline comments:** {len(result.comments)}",
        f"**Generic comment ratio:** {result.generic_ratio:.0%}",
        f"**Recommendation:** {rec_text}",
    ])


async def post_bitbucket_comment(
    repo: str,
    pr_number: int,
    result: AnalysisResult,
    token: str | None = None,
) -> str:
    """Post analysis as a Bitbucket Cloud PR comment + inline comments.

    Returns the ID of the summary comment as a string.
    """
    workspace, _, repo_slug = repo.partition("/")
    comments_url = (
        f"{_BITBUCKET_API_BASE}/repositories/{workspace}/{repo_slug}"
        f"/pullrequests/{pr_number}/comments"
    )

    headers = _bitbucket_auth_headers(token)
    summary_body = _build_bitbucket_summary_body(result)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            comments_url,
            json={"content": {"raw": summary_body}},
            headers=headers,
        )

    if resp.status_code == 429:
        raise RateLimitError("429 from Bitbucket")
    if resp.status_code >= 500:
        resp.raise_for_status()
    if resp.status_code >= 400:
        raise BitbucketClientError(f"Bitbucket {resp.status_code}: {resp.text[:300]}")

    comment_id = str(resp.json()["id"])

    # Post inline comments; a 4xx on a specific position is skipped to not block the summary.
    async with httpx.AsyncClient(timeout=30.0) as client:
        for comment in result.comments:
            if comment.line <= 0 or not comment.file:
                continue
            body = f"{comment.body}\n\n*Confidence: {comment.confidence:.0%} — {comment.rationale}*"
            inline_payload: dict[str, Any] = {
                "content": {"raw": body},
                "inline": {"to": comment.line, "path": comment.file},
            }
            inline_resp = await client.post(comments_url, json=inline_payload, headers=headers)
            if inline_resp.status_code == 429:
                raise RateLimitError("429 from Bitbucket (inline comment)")
            if inline_resp.status_code >= 500:
                inline_resp.raise_for_status()
            if inline_resp.status_code >= 400:
                logger.warning(
                    "skipping inline comment on %s:%d — Bitbucket %d: %s",
                    comment.file,
                    comment.line,
                    inline_resp.status_code,
                    inline_resp.text[:200],
                )

    return comment_id
