import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from app.llm.db_config import load_llm_config_from_db  # noqa: E402

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_pool(row):
    """Return a mock asyncpg pool whose acquire() context yields a conn returning row."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=row)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_async_ctx(conn))
    return pool


class _async_ctx:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *_):
        pass


def _make_key() -> str:
    return Fernet.generate_key().decode()


def _encrypt(plaintext: str, key: str) -> str:
    return Fernet(key.encode()).encrypt(plaintext.encode()).decode()


# ---------------------------------------------------------------------------
# load_llm_config_from_db — DB path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_db_config_returns_none_when_no_row():
    pool = _make_pool(None)
    result = await load_llm_config_from_db(pool)
    assert result is None


@pytest.mark.asyncio
async def test_db_config_returns_dict_without_api_key():
    row = {
        "provider": "ollama",
        "base_url": "http://ollama:11434",
        "model": "llama3.1:8b",
        "api_key": None,
        "extra": {},
    }
    pool = _make_pool(row)
    result = await load_llm_config_from_db(pool)
    assert result == {
        "provider": "ollama",
        "base_url": "http://ollama:11434",
        "model": "llama3.1:8b",
        "api_key": "",
        "extra": {},
    }


@pytest.mark.asyncio
async def test_db_config_decrypts_api_key():
    key = _make_key()
    encrypted = _encrypt("sk-real-key", key)
    row = {
        "provider": "openai",
        "base_url": None,
        "model": "gpt-4o",
        "api_key": encrypted,
        "extra": {},
    }
    pool = _make_pool(row)
    env = {k: v for k, v in os.environ.items() if k != "LLM_ENCRYPTION_KEY"}
    env["LLM_ENCRYPTION_KEY"] = key
    with patch.dict(os.environ, env, clear=True):
        result = await load_llm_config_from_db(pool)
    assert result["api_key"] == "sk-real-key"
    assert result["provider"] == "openai"
    assert result["base_url"] == ""


@pytest.mark.asyncio
async def test_db_config_raises_on_wrong_encryption_key(tmp_path):
    """Ciphertext produced with key A must fail to decrypt with key B."""
    from cryptography.fernet import InvalidToken

    encrypted = _encrypt("sk-real-key", _make_key())  # encrypted with a throwaway key
    row = {
        "provider": "openai",
        "base_url": None,
        "model": "gpt-4o",
        "api_key": encrypted,
        "extra": {},
    }
    pool = _make_pool(row)
    wrong_key = _make_key()
    env = {k: v for k, v in os.environ.items() if k != "LLM_ENCRYPTION_KEY"}
    env["LLM_ENCRYPTION_KEY"] = wrong_key
    env["VELLIC_SECRETS_DIR"] = str(tmp_path)
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(InvalidToken):
            await load_llm_config_from_db(pool)


