"""Load VCS credentials from ``webhook_config`` (DB)."""

from __future__ import annotations

import logging

import asyncpg

from .crypto import decrypt

logger = logging.getLogger("worker.vcs_tokens")


async def _fetch_column(pool: asyncpg.Pool, column: str) -> str:
    try:
        row = await pool.fetchrow(f"SELECT {column} FROM webhook_config WHERE id = 1")
    except asyncpg.exceptions.UndefinedTableError:
        return ""
    except Exception as exc:
        logger.warning("failed to read webhook_config.%s: %s", column, exc)
        return ""
    try:
        value = row[column] if row else None
    except (KeyError, TypeError):
        return ""
    if not value:
        return ""
    try:
        return decrypt(value)
    except Exception as exc:
        logger.warning("failed to decrypt webhook_config.%s: %s", column, exc)
        return ""


async def get_github_token(pool: asyncpg.Pool) -> str:
    return await _fetch_column(pool, "github_token")


async def get_gitlab_token(pool: asyncpg.Pool) -> str:
    return await _fetch_column(pool, "gitlab_token")
