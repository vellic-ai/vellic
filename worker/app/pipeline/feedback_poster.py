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


class GitLabClientError(Exception):
    """Terminal 4xx error from GitLab (not 429)."""


_GITLAB_API_BASE = os.getenv("GITLAB_API_URL", "https://gitlab.com/api/v4")


def _build_gitlab_note_body(result: AnalysisResult) -> str:
    """Return the plain-text body for a GitLab MR discussion note."""
    body, _ = _build_review_body(result)
    return body


async def post_gitlab_discussion(
    repo: str,
    mr_iid: int,
    commit_sha: str,
    result: AnalysisResult,
    token: str | None = None,
) -> str:
    """Post analysis as a GitLab MR discussion note plus inline position notes.

    Returns the discussion ID of the summary note.
    """
    resolved_token = token or os.getenv("GITLAB_TOKEN", "")
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if resolved_token:
        headers["PRIVATE-TOKEN"] = resolved_token

    body = _build_gitlab_note_body(result)
    project_path = quote(repo, safe="")
    url = f"{_GITLAB_API_BASE}/projects/{project_path}/merge_requests/{mr_iid}/discussions"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json={"body": body}, headers=headers)

        if resp.status_code == 429:
            raise RateLimitError("429 from GitLab")
        if resp.status_code >= 500:
            resp.raise_for_status()
        if resp.status_code >= 400:
            raise GitLabClientError(f"GitLab {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        note_id = str(data["id"])

        # Post per-line position notes (best-effort; skip invalid positions).
        inline_comments = [c for c in result.comments if c.line > 0 and c.file]
        for c in inline_comments:
            inline_payload = {
                "body": f"{c.body}\n\n*Confidence: {c.confidence:.0%} — {c.rationale}*",
                "position": {
                    "base_sha": "",
                    "start_sha": commit_sha,
                    "head_sha": commit_sha,
                    "position_type": "text",
                    "new_path": c.file,
                    "new_line": c.line,
                },
            }
            inline_resp = await client.post(url, json=inline_payload, headers=headers)
            if inline_resp.status_code == 429:
                raise RateLimitError("429 from GitLab inline")
            if inline_resp.status_code == 422 or (
                400 <= inline_resp.status_code < 500
            ):
                logger.warning(
                    "gitlab inline comment rejected %s:%d status=%d — skipping",
                    c.file,
                    c.line,
                    inline_resp.status_code,
                )
                continue

    return note_id


# ---------------------------------------------------------------------------
# Bitbucket
# ---------------------------------------------------------------------------

_BITBUCKET_API_BASE = "https://api.bitbucket.org/2.0"


class BitbucketClientError(Exception):
    """Terminal 4xx error from Bitbucket (not 429)."""


def _build_bitbucket_summary_body(result: AnalysisResult) -> str:
    """Return the plain-text body for a Bitbucket PR comment."""
    body, _ = _build_review_body(result)
    return body


def _bitbucket_auth_headers() -> dict[str, str]:
    token = os.getenv("BITBUCKET_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    username = os.getenv("BITBUCKET_USERNAME", "")
    app_password = os.getenv("BITBUCKET_APP_PASSWORD", "")
    if username and app_password:
        encoded = base64.b64encode(f"{username}:{app_password}".encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    return {}


async def post_bitbucket_comment(
    repo: str,
    pr_number: int,
    result: AnalysisResult,
    token: str | None = None,
) -> str:
    """Post analysis as a Bitbucket PR comment plus inline comments.

    Returns the ID of the summary comment as a string.
    """
    if token:
        headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
    else:
        headers = _bitbucket_auth_headers()
    headers["Content-Type"] = "application/json"

    owner, _, slug = repo.partition("/")
    base_url = (
        f"{_BITBUCKET_API_BASE}/repositories/{owner}/{slug}/pullrequests/{pr_number}/comments"
    )

    body = _build_bitbucket_summary_body(result)
    summary_payload = {"content": {"raw": body}}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(base_url, json=summary_payload, headers=headers)

        if resp.status_code == 429:
            raise RateLimitError("429 from Bitbucket")
        if resp.status_code >= 500:
            resp.raise_for_status()
        if resp.status_code >= 400:
            raise BitbucketClientError(f"Bitbucket {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        comment_id = str(data["id"])

        # Post per-line inline comments (best-effort).
        inline_comments = [c for c in result.comments if c.line > 0 and c.file]
        for c in inline_comments:
            inline_payload = {
                "content": {
                    "raw": f"{c.body}\n\n*Confidence: {c.confidence:.0%} — {c.rationale}*"
                },
                "inline": {"to": c.line, "path": c.file},
            }
            inline_resp = await client.post(base_url, json=inline_payload, headers=headers)
            if inline_resp.status_code == 429:
                raise RateLimitError("429 from Bitbucket inline")
            if 400 <= inline_resp.status_code < 500:
                logger.warning(
                    "bitbucket inline comment rejected %s:%d status=%d — skipping",
                    c.file,
                    c.line,
                    inline_resp.status_code,
                )
                continue

    return comment_id
