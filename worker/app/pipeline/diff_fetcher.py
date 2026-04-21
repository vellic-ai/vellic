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


def _parse_unified_diff(text: str) -> list[tuple[str, str]]:
    """Parse a raw unified diff into (filename, patch) pairs.

    Handles the format returned by Bitbucket's pullrequests/{id}/diff endpoint.
    """
    files: list[tuple[str, str]] = []
    current_file: str | None = None
    patch_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("+++ b/"):
            if current_file is not None:
                files.append((current_file, "\n".join(patch_lines)))
            current_file = line[6:]
            patch_lines = []
        elif line.startswith("+++ /dev/null"):
            if current_file is not None:
                files.append((current_file, "\n".join(patch_lines)))
            current_file = None
            patch_lines = []
        elif current_file is not None:
            patch_lines.append(line)

    if current_file is not None:
        files.append((current_file, "\n".join(patch_lines)))

    return files


async def fetch_diff_chunks(
    diff_url: str,
    platform: str = "github",
    token: str | None = None,
    platform: str = "github",
) -> list[DiffChunk]:
    """Fetch and chunk PR file diffs from a platform files/diff URL.

    GitHub and GitLab return JSON (array or {"changes": [...]}). Bitbucket
    returns a raw unified diff text that is parsed locally.
    """
    validate_outbound_url(diff_url, context="diff_fetcher")

    if platform == "bitbucket":
        bb_token = token or os.getenv("BITBUCKET_TOKEN", "")
        bb_user = os.getenv("BITBUCKET_USERNAME", "")
        bb_pass = os.getenv("BITBUCKET_APP_PASSWORD", "")
        headers: dict[str, str] = {"Accept": "text/plain"}
        auth: tuple[str, str] | None = None
        if bb_token:
            headers["Authorization"] = f"Bearer {bb_token}"
        elif bb_user and bb_pass:
            auth = (bb_user, bb_pass)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(diff_url, headers=headers, auth=auth)
            resp.raise_for_status()
            raw_diff = resp.text

        file_pairs = _parse_unified_diff(raw_diff)
        chunks: list[DiffChunk] = []
        for filename, patch in file_pairs:
            if not patch.strip():
                logger.debug("skipping %s: no patch (binary or empty)", filename)
                continue
            if _is_generated(filename):
                logger.info("skipping generated file: %s", filename)
                continue
            chunks.extend(_chunk_patch(filename, patch))

        logger.info(
            "fetched %d chunks from %d files via %s (bitbucket raw diff)",
            len(chunks),
            len(file_pairs),
            diff_url,
        )
        return chunks

    resolved_token = token or os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/json"}
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(diff_url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # GitHub returns a JSON array; GitLab changes API returns {"changes": [...]}
    if isinstance(data, dict):
        files_list = data.get("changes", [])
    else:
        files_list = data

    chunks = []
    for file_info in files_list:
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

    logger.info("fetched %d chunks from %d files via %s", len(chunks), len(files_list), diff_url)
    return chunks
