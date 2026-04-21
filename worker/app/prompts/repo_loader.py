"""Load prompts for a repo — DB-first, file fallback (VEL-134).

Merge strategy (VEL-134 UI-as-source-of-truth):
  - Primary source: prompt_overrides rows in DB for this repo_id.
  - Fallback: .vellic/prompts/*.md files in the checked-out repo, used only
    when the DB has zero records for this repo.
  - Disabled DB entries (enabled=FALSE) are excluded from the result.

Previous behaviour (VEL-115): repo files were primary, DB shadowed them.
VEL-134 inverts this: DB is authoritative; files are export/import only.
"""

from __future__ import annotations

import logging

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

    DB is primary. If DB has records for this repo, returns those (filtering
    out disabled entries). Falls back to .vellic/prompts/*.md only when the
    DB has no records at all for this repo.

    Returns an empty list immediately when the ``platform.prompt_dsl`` flag is
    disabled so callers fall back to legacy prompt behaviour.
    """
    if not _flag_enabled("platform.prompt_dsl"):
        logger.debug("platform.prompt_dsl disabled — skipping prompt DSL load for repo=%s", repo_id)
        return []

    overrides = await list_overrides(conn, repo_id)

    if overrides:
        # DB is source of truth — parse all enabled DB entries
        result: list[PromptFile] = []
        for row in overrides:
            if not row.get("enabled", True):
                logger.debug("skipping disabled prompt repo=%s name=%s", repo_id, row["path"])
                continue
            path: str = row["path"]
            body: str = row["body"]
            try:
                pf = parse_prompt_content(body, name=path, path="", source="db")
                result.append(pf)
                logger.debug("db prompt loaded: repo=%s name=%s", repo_id, path)
            except Exception as exc:
                logger.warning(
                    "skipping malformed db prompt repo=%s name=%s: %s", repo_id, path, exc
                )
        logger.info(
            "prompt load (db-primary) repo=%s db_rows=%d enabled=%d",
            repo_id,
            len(overrides),
            len(result),
        )
        return result

    # No DB records — fall back to repo files
    prompts_dir = find_repo_prompts_dir(checkout_path)
    repo_files = load_prompts_from_dir(prompts_dir)
    logger.info("prompt load (file-fallback) repo=%s files=%d", repo_id, len(repo_files))
    return repo_files


def load_repo_prompts_sync(checkout_path: str) -> list[PromptFile]:
    """Load repo prompts without DB (file fallback only). Useful in sync contexts.

    Returns an empty list when ``platform.prompt_dsl`` is disabled.
    """
    if not _flag_enabled("platform.prompt_dsl"):
        logger.debug("platform.prompt_dsl disabled — skipping prompt DSL load (sync)")
        return []
    prompts_dir = find_repo_prompts_dir(checkout_path)
    return load_prompts_from_dir(prompts_dir)
