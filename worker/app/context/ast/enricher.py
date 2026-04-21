"""Enriches DiffChunks with AST symbol context extracted from diff patch lines."""
from __future__ import annotations

import logging
import re

from ...pipeline.models import DiffChunk
from .models import ASTContext
from .registry import get_parser

logger = logging.getLogger("worker.context.ast.enricher")

_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _extract_source_from_patch(patch_lines: list[str]) -> tuple[str, list[int]]:
    """
    Reconstruct new-side source from unified diff lines.

    Returns (source_text, new_line_numbers) where new_line_numbers[i] is the
    1-based line number in the new file for source_text.splitlines()[i].
    """
    lines: list[str] = []
    line_numbers: list[int] = []
    current_new_line = 1

    for raw in patch_lines:
        m = _HUNK_HEADER.match(raw)
        if m:
            current_new_line = int(m.group(1))
            continue
        if raw.startswith("-"):
            continue
        if raw.startswith("+"):
            lines.append(raw[1:])
            line_numbers.append(current_new_line)
            current_new_line += 1
        else:
            # context line
            lines.append(raw[1:] if raw.startswith(" ") else raw)
            line_numbers.append(current_new_line)
            current_new_line += 1

    return "\n".join(lines), line_numbers


def _changed_line_numbers(patch_lines: list[str]) -> list[int]:
    """Return the new-file line numbers that were added (+) in the patch."""
    changed: list[int] = []
    current_new_line = 1

    for raw in patch_lines:
        m = _HUNK_HEADER.match(raw)
        if m:
            current_new_line = int(m.group(1))
            continue
        if raw.startswith("+"):
            changed.append(current_new_line)
            current_new_line += 1
        elif raw.startswith("-"):
            pass
        else:
            current_new_line += 1

    return changed


class ASTEnricher:
    """
    Stateless enricher: for each DiffChunk, parses the reconstructed source
    and returns the symbols that contain changed lines.

    Usage::

        enricher = ASTEnricher()
        for chunk in diff_chunks:
            ctx = enricher.enrich(chunk)
            # ctx.symbols contains functions/classes that have changed lines
    """

    def enrich(self, chunk: DiffChunk) -> ASTContext:
        provider = get_parser(chunk.filename)
        if provider is None:
            return ASTContext(filename=chunk.filename, language="unknown")

        source, _ = _extract_source_from_patch(chunk.patch_lines)
        changed_lines = _changed_line_numbers(chunk.patch_lines)

        ast_ctx = provider.parse(chunk.filename, source)
        if ast_ctx.parse_error:
            logger.debug("parse error %s: %s", chunk.filename, ast_ctx.parse_error)
            return ast_ctx

        ast_ctx.symbols = ast_ctx.symbols_for_lines(changed_lines)
        return ast_ctx

    def enrich_all(self, chunks: list[DiffChunk]) -> dict[str, ASTContext]:
        """Return a mapping filename → ASTContext for all supported chunks.

        A single file may appear in multiple DiffChunk objects when diff_fetcher
        splits large files at 500-line boundaries.  We merge all patch lines per
        filename before parsing so that the symbol graph covers the whole file.
        """
        from collections import defaultdict
        grouped: dict[str, list[str]] = defaultdict(list)
        for chunk in chunks:
            grouped[chunk.filename].extend(chunk.patch_lines)
        return {
            filename: self.enrich(DiffChunk(filename=filename, patch_lines=patch_lines))
            for filename, patch_lines in grouped.items()
        }
