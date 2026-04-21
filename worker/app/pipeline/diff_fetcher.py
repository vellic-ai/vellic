import logging
import os

import httpx

from ..security.ssrf import validate_outbound_url
from .models import DiffChunk

logger = logging.getLogger("worker.pipeline.diff_fetcher")

_MAX_LINES_PER_CHUNK = 500

_SKIP_SUFFIXES = (".lock", "-lock.json", "-lock.yaml")
_SKIP_PATH_SEGMENTS = ("dist/", "node_modules/", ".min.js", ".min.css", "vendor/", "generated/")


def _is_generated(filename: str) -> bool:
    if any(filename.endswith(s) for s in _SKIP_SUFFIXES):
        return True
    if any(seg in filename for seg in _SKIP_PATH_SEGMENTS):
        return True
    return False


def _chunk_patch(filename: str, patch: str) -> list[DiffChunk]:
    lines = patch.splitlines()
    chunks = []
    for start in range(0, max(len(lines), 1), _MAX_LINES_PER_CHUNK):
        chunk_lines = lines[start : start + _MAX_LINES_PER_CHUNK]
        if chunk_lines:
            chunks.append(DiffChunk(filename=filename, patch_lines=chunk_lines))
    return chunks


async def fetch_diff_chunks(
    diff_url: str,
    token: str | None = None,
) -> list[DiffChunk]:
    """Fetch and chunk PR file diffs from a platform files API URL.

    The URL is expected to return a JSON array of file objects, each with
    ``filename`` and optional ``patch`` fields — the shape returned by both
    the GitHub and GitLab files/changes APIs.
    """
    validate_outbound_url(diff_url, context="diff_fetcher")

    resolved_token = token or os.getenv("GITHUB_TOKEN", "")
    headers: dict[str, str] = {"Accept": "application/json"}
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(diff_url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # GitHub returns a JSON array; GitLab changes API returns {"changes": [...]}
    if isinstance(data, dict):
        files = data.get("changes", [])
    else:
        files = data

    chunks: list[DiffChunk] = []
    for file_info in files:
        # GitHub: filename/patch; GitLab: new_path/diff
        filename = file_info.get("filename") or file_info.get("new_path", "")
        patch = file_info.get("patch") or file_info.get("diff", "")

        if not patch:
            logger.debug("skipping %s: no patch (binary or empty)", filename)
            continue

        if _is_generated(filename):
            logger.info("skipping generated file: %s", filename)
            continue

        chunks.extend(_chunk_patch(filename, patch))

    logger.info("fetched %d chunks from %d files via %s", len(chunks), len(files), diff_url)
    return chunks
