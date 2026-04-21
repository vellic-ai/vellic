"""Context-variable resolver for prompt templates (VEL-111).

Builds a PromptContext from pipeline data so prompt templates can reference
variables like {{ diff }}, {{ symbols }}, {{ changed_files }}, etc.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from ..pipeline.models import DiffChunk, PRContext
from .models import PromptContext

if TYPE_CHECKING:
    import asyncpg  # noqa: F401

logger = logging.getLogger("worker.prompts.context_resolver")

# Matches common symbol declarations in unified-diff added lines.
# Captures function / method / class names across Python, JS/TS, Go, Rust.
_SYMBOL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\+\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)"),          # Python func
    re.compile(r"^\+\s*class\s+([A-Za-z_][A-Za-z0-9_]*)"),                      # Python/JS class
    re.compile(r"^\+\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)"),  # JS/TS
    re.compile(  # arrow func
        r"^\+\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?\("
    ),
    re.compile(r"^\+\s*func\s+(?:\([^)]+\)\s+)?([A-Za-z_][A-Za-z0-9_]*)"),      # Go func/method
    re.compile(r"^\+\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)"), # Rust fn
]

_MAX_DIFF_CHARS = 40_000
_MAX_PREV_REVIEWS = 5


def build_diff_text(chunks: list[DiffChunk]) -> str:
    """Concatenate diff chunks into a single string, truncated to _MAX_DIFF_CHARS."""
    parts: list[str] = []
    total = 0
    for chunk in chunks:
        header = f"### {chunk.filename}\n```diff\n"
        footer = "\n```\n"
        segment = header + chunk.patch + footer
        if total + len(segment) > _MAX_DIFF_CHARS:
            remaining = _MAX_DIFF_CHARS - total - len(header) - len(footer)
            if remaining > 0:
                parts.append(header + chunk.patch[:remaining] + "\n[truncated]\n" + footer)
            break
        parts.append(segment)
        total += len(segment)
    return "".join(parts)


def extract_symbols_from_diff(chunks: list[DiffChunk]) -> str:
    """Extract symbol names touched in added lines across all diff chunks.

    Returns a newline-separated string of "filename: symbol_name" entries.
    Duplicates per file are removed; order is preserved.
    """
    lines: list[str] = []
    for chunk in chunks:
        seen: set[str] = set()
        for raw_line in chunk.patch_lines:
            for pattern in _SYMBOL_PATTERNS:
                m = pattern.match(raw_line)
                if m:
                    name = m.group(1)
                    if name not in seen:
                        seen.add(name)
                        lines.append(f"{chunk.filename}: {name}")
                    break
    return "\n".join(lines)


def get_changed_files(chunks: list[DiffChunk]) -> list[str]:
    """Return deduplicated list of filenames that appear in the diff, preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for chunk in chunks:
        if chunk.filename not in seen:
            seen.add(chunk.filename)
            result.append(chunk.filename)
    return result


async def fetch_prev_reviews(
    pool: asyncpg.Pool,
    repo: str,
    pr_number: int,
    limit: int = _MAX_PREV_REVIEWS,
) -> list[str]:
    """Query past review summaries for this PR from the database.

    Returns a list of summary strings ordered oldest-first, capped at *limit*.
    Returns an empty list if no prior reviews exist or on any DB error.
    """
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT feedback->>'summary' AS summary
                FROM pr_reviews
                WHERE repo = $1 AND pr_number = $2
                  AND feedback->>'summary' IS NOT NULL
                  AND feedback->>'summary' != ''
                ORDER BY posted_at ASC NULLS LAST
                LIMIT $3
                """,
                repo,
                pr_number,
                limit,
            )
        return [row["summary"] for row in rows]
    except Exception:
        logger.warning(
            "failed to fetch prev_reviews for %s#%d", repo, pr_number, exc_info=True
        )
        return []


def build_prompt_context(
    pr_ctx: PRContext,
    chunks: list[DiffChunk],
    labels: list[str] | None = None,
    prev_reviews: list[str] | None = None,
    coverage: str = "",
    extra: dict[str, str] | None = None,
) -> PromptContext:
    """Build a PromptContext from pipeline-stage data.

    Args:
        pr_ctx: PR metadata gathered in pipeline stage 1.
        chunks: Diff chunks fetched in pipeline stage 2.
        labels: PR label names from the webhook event.
        prev_reviews: Prior review summaries fetched from DB (or None to skip).
        coverage: Raw coverage report string (empty until coverage stage exists).
        extra: Caller-supplied overrides for any variable.
    """
    return PromptContext(
        diff=build_diff_text(chunks),
        symbols=extract_symbols_from_diff(chunks),
        coverage=coverage,
        prev_reviews=list(prev_reviews) if prev_reviews else [],
        pr_title=pr_ctx.title,
        pr_body=pr_ctx.body,
        repo=pr_ctx.repo,
        base_branch=pr_ctx.base_branch,
        changed_files=get_changed_files(chunks),
        labels=list(labels) if labels else [],
        extra=dict(extra) if extra else {},
    )
