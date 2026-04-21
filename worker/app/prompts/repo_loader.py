"""Load prompts from a repo checkout, merged with DB overrides (VEL-115).

Merge strategy:
  - Primary source: .vellic/prompts/*.md files in the checked-out repo.
  - Override source: prompt_overrides rows in DB for this repo_id.
  - DB override wins over a repo file when both supply the same prompt name.
    (The DB entry represents an in-progress UI edit not yet committed.)
  - DB-only entries (no matching repo file) are included as additional prompts.
"""

from __future__ import annotations

import logging
from pathlib import Path

import asyncpg
from vellic_flags import by_key

from .models import PromptFile
from .parser import find_repo_prompts_dir, load_prompts_from_dir, parse_prompt_content
from .store import list_overrides

logger = logging.getLogger("worker.prompts.repo_loader")


def _flag_enabled(key: str) -> bool:
    flag = by_key(key)
    if flag is None:
        return False
    env = flag.read_env()
    return env if env is not None else flag.default


async def load_repo_prompts(
    checkout_path: str,
    repo_id: str,
    conn: asyncpg.Connection,
) -> list[PromptFile]:
    """Return the effective prompt list for *repo_id*.

    Reads `.vellic/prompts/` from *checkout_path*, then overlays any DB
    overrides stored under *repo_id*.  DB entries shadow matching repo files;
    DB-only entries are appended.

    Returns an empty list immediately when the ``platform.prompt_dsl`` flag is
    disabled so callers fall back to legacy prompt behaviour.
    """
    if not _flag_enabled("platform.prompt_dsl"):
        logger.debug("platform.prompt_dsl disabled — skipping prompt DSL load for repo=%s", repo_id)
        return []

    prompts_dir = find_repo_prompts_dir(checkout_path)
    repo_files: list[PromptFile] = load_prompts_from_dir(prompts_dir)
    repo_map: dict[str, PromptFile] = {p.name: p for p in repo_files}

    overrides = await list_overrides(conn, repo_id)
    if not overrides:
        return repo_files

    override_map: dict[str, PromptFile] = {}
    for row in overrides:
        path: str = row["path"]  # e.g. "secure-review"
        body: str = row["body"]
        try:
            pf = parse_prompt_content(body, name=path, path="", source="db")
            override_map[path] = pf
            logger.debug("db override loaded: repo=%s name=%s", repo_id, path)
        except Exception as exc:
            logger.warning("skipping malformed db override repo=%s name=%s: %s", repo_id, path, exc)

    merged: dict[str, PromptFile] = {**repo_map, **override_map}
    result = list(merged.values())
    logger.info(
        "prompt merge complete repo=%s repo_files=%d overrides=%d total=%d",
        repo_id,
        len(repo_files),
        len(override_map),
        len(result),
    )
    return result


def load_repo_prompts_sync(checkout_path: str) -> list[PromptFile]:
    """Load repo prompts without DB (no overrides). Useful in sync contexts.

    Returns an empty list when ``platform.prompt_dsl`` is disabled.
    """
    if not _flag_enabled("platform.prompt_dsl"):
        logger.debug("platform.prompt_dsl disabled — skipping prompt DSL load (sync)")
        return []
    prompts_dir = find_repo_prompts_dir(checkout_path)
    return load_prompts_from_dir(prompts_dir)
