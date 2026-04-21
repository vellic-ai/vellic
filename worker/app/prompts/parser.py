"""Parse .vellic/prompts/*.md files into PromptFile objects (VEL-109)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

from .models import PromptFile
from .schema import PromptValidationError, validate_frontmatter

logger = logging.getLogger("worker.prompts.parser")

_FRONTMATTER_DELIMITER = "---"


def _split_frontmatter(content: str, source_hint: str) -> tuple[str, str]:
    """Split *content* into (front-matter YAML, body).

    Expects the file to start with '---', followed by YAML, followed by another '---'.
    Raises :class:`PromptValidationError` when the delimiter structure is wrong.
    """
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
        raise PromptValidationError(
            f"Prompt file {source_hint!r} must start with '---' (YAML front-matter delimiter)"
        )

    end_idx: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == _FRONTMATTER_DELIMITER:
            end_idx = i
            break

    if end_idx is None:
        raise PromptValidationError(
            f"Prompt file {source_hint!r} has no closing '---' for front-matter"
        )

    frontmatter_yaml = "".join(lines[1:end_idx])
    body = "".join(lines[end_idx + 1 :]).lstrip("\n")
    return frontmatter_yaml, body


def parse_prompt_content(content: str, name: str, path: str = "", source: str = "repo") -> PromptFile:
    """Parse *content* (a full .md file string) into a :class:`PromptFile`.

    Raises :class:`PromptValidationError` on invalid front-matter.
    """
    frontmatter_yaml, body = _split_frontmatter(content, source_hint=name)

    try:
        raw = yaml.safe_load(frontmatter_yaml) or {}
    except yaml.YAMLError as exc:
        raise PromptValidationError(
            f"YAML parse error in {name!r}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise PromptValidationError(
            f"Front-matter in {name!r} must be a YAML mapping, got {type(raw).__name__}"
        )

    frontmatter = validate_frontmatter(raw, source_hint=name)
    return PromptFile(name=name, path=path, frontmatter=frontmatter, body=body, source=source)


def load_prompts_from_dir(prompts_dir: str | Path) -> list[PromptFile]:
    """Load all *.md files from *prompts_dir* as prompt files.

    Files that fail validation are logged and skipped (fail-fast per file, not per directory).
    Returns an empty list when the directory does not exist.
    """
    base = Path(prompts_dir)
    if not base.is_dir():
        logger.debug("prompts directory %s does not exist — no custom prompts", base)
        return []

    results: list[PromptFile] = []
    for entry in sorted(base.iterdir()):
        if entry.suffix != ".md":
            continue
        name = entry.stem
        try:
            content = entry.read_text(encoding="utf-8")
            prompt = parse_prompt_content(content, name=name, path=str(entry), source="repo")
            results.append(prompt)
            logger.debug("loaded prompt %r from %s", name, entry)
        except PromptValidationError as exc:
            # Fail-fast per file: log and skip rather than silently ignoring.
            logger.error("invalid prompt file %s: %s", entry, exc)
            raise
        except OSError as exc:
            logger.warning("could not read prompt file %s: %s", entry, exc)

    logger.info("loaded %d prompt(s) from %s", len(results), base)
    return results


def find_repo_prompts_dir(repo_checkout_path: str) -> str:
    """Return the canonical prompts directory for a checked-out repo."""
    return os.path.join(repo_checkout_path, ".vellic", "prompts")
