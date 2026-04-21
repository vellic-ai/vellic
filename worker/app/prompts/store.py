"""DB CRUD for the prompt_overrides table (VEL-115).

Schema: prompt_overrides(id, repo_id, path, body, updated_at)
  - repo_id: the repo full name (e.g. "org/repo")
  - path: prompt identifier — matches the .md filename stem under .vellic/prompts/
  - body: full raw prompt file content (frontmatter + body)
  - UNIQUE (repo_id, path)
"""

from __future__ import annotations

from datetime import datetime

import asyncpg


async def list_overrides(conn: asyncpg.Connection, repo_id: str) -> list[dict]:
    """Return all prompt overrides for *repo_id*, ordered by path."""
    rows = await conn.fetch(
        "SELECT path, body, enabled, updated_at FROM prompt_overrides WHERE repo_id = $1 ORDER BY path",
        repo_id,
    )
    return [dict(r) for r in rows]


async def get_override(
    conn: asyncpg.Connection, repo_id: str, path: str
) -> dict | None:
    """Return a single override or None if it does not exist."""
    row = await conn.fetchrow(
        "SELECT path, body, enabled, updated_at FROM prompt_overrides WHERE repo_id = $1 AND path = $2",
        repo_id,
        path,
    )
    return dict(row) if row else None


async def upsert_override(
    conn: asyncpg.Connection, repo_id: str, path: str, body: str
) -> datetime:
    """Insert or replace a prompt override. Returns the stored updated_at timestamp."""
    row = await conn.fetchrow(
        """
        INSERT INTO prompt_overrides (repo_id, path, body)
        VALUES ($1, $2, $3)
        ON CONFLICT (repo_id, path) DO UPDATE
            SET body = EXCLUDED.body,
                updated_at = NOW()
        RETURNING updated_at
        """,
        repo_id,
        path,
        body,
    )
    return row["updated_at"]  # type: ignore[index]


async def delete_override(conn: asyncpg.Connection, repo_id: str, path: str) -> bool:
    """Delete an override. Returns True if a row was deleted."""
    result = await conn.execute(
        "DELETE FROM prompt_overrides WHERE repo_id = $1 AND path = $2",
        repo_id,
        path,
    )
    return result != "DELETE 0"
