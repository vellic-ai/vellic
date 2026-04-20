import logging
import os

import httpx

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
    # package-lock and yarn.lock are caught by .lock suffix above
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
    repo: str,
    pr_number: int,
    github_token: str | None = None,
) -> list[DiffChunk]:
    token = github_token or os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(base_url="https://api.github.com", timeout=30.0) as client:
        resp = await client.get(f"/repos/{repo}/pulls/{pr_number}/files", headers=headers)
        resp.raise_for_status()
        files = resp.json()

    chunks: list[DiffChunk] = []
    for file_info in files:
        filename = file_info.get("filename", "")
        patch = file_info.get("patch", "")

        if not patch:
            logger.debug("skipping %s: no patch (binary or empty)", filename)
            continue

        if _is_generated(filename):
            logger.info("skipping generated file: %s", filename)
            continue

        chunks.extend(_chunk_patch(filename, patch))

    logger.info("fetched %d chunks from %d files for %s#%d", len(chunks), len(files), repo, pr_number)
    return chunks
