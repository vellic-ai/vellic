import logging
import os

import asyncpg
from cryptography.fernet import Fernet

logger = logging.getLogger("worker.llm.db_config")


def _decrypt(ciphertext: str) -> str:
    key = os.environ.get("LLM_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("LLM_ENCRYPTION_KEY env var is not set")
    raw = key.encode() if isinstance(key, str) else key
    return Fernet(raw).decrypt(ciphertext.encode()).decode()


async def load_llm_config_from_db(pool: asyncpg.Pool) -> dict | None:
    """Return LLM config dict from the llm_settings row, or None if not configured."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM llm_settings WHERE id = 1")
    if row is None:
        return None
    row = dict(row)
    api_key = _decrypt(row["api_key"]) if row.get("api_key") else ""
    return {
        "provider": row["provider"],
        "base_url": row["base_url"] or "",
        "model": row["model"],
        "api_key": api_key,
        "extra": row.get("extra") or {},
    }
