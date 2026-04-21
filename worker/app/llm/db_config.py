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


async def load_repo_llm_config_from_db(
    pool: asyncpg.Pool, installation_id: str
) -> dict | None:
    """Return per-repo LLM config from llm_configs, or None if not set.

    Resolution order callers should apply: this result > global llm_settings > env vars.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT provider, model, base_url, api_key_enc"
            " FROM llm_configs WHERE installation_id = $1::uuid",
            installation_id,
        )
    if row is None:
        return None
    row = dict(row)
    api_key = ""
    if row.get("api_key_enc"):
        try:
            api_key = _decrypt(row["api_key_enc"])
        except Exception as exc:
            logger.warning(
                "failed to decrypt api_key_enc for installation %s: %s", installation_id, exc
            )
    return {
        "provider": row["provider"],
        "base_url": row.get("base_url") or "",
        "model": row["model"],
        "api_key": api_key,
        "extra": {},
    }
