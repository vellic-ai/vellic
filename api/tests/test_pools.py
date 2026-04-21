"""Tests for api/app/db.py and api/app/arq_pool.py pool helpers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# db.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_init_pool_creates_pool(monkeypatch):
    import app.db as db_mod

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")
    db_mod._pool = None
    fake_pool = MagicMock()

    with patch("app.db.asyncpg.create_pool", new=AsyncMock(return_value=fake_pool)):
        await db_mod.init_pool()

    assert db_mod._pool is fake_pool
    db_mod._pool = None


@pytest.mark.asyncio
async def test_db_close_pool_closes_and_clears(monkeypatch):
    import app.db as db_mod

    fake_pool = AsyncMock()
    db_mod._pool = fake_pool

    await db_mod.close_pool()

    fake_pool.close.assert_called_once()
    assert db_mod._pool is None


@pytest.mark.asyncio
async def test_db_close_pool_noop_when_none():
    import app.db as db_mod

    db_mod._pool = None
    await db_mod.close_pool()  # must not raise


def test_db_get_pool_returns_pool_when_initialized():
    import app.db as db_mod

    fake_pool = MagicMock()
    db_mod._pool = fake_pool

    result = db_mod.get_pool()
    assert result is fake_pool
    db_mod._pool = None


def test_db_get_pool_raises_when_not_initialized():
    import app.db as db_mod

    db_mod._pool = None
    with pytest.raises(RuntimeError, match="not initialized"):
        db_mod.get_pool()


# ---------------------------------------------------------------------------
# arq_pool.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arq_init_pool_creates_pool(monkeypatch):
    import app.arq_pool as arq_mod

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    arq_mod._pool = None
    fake_pool = MagicMock()

    with patch("app.arq_pool.create_pool", new=AsyncMock(return_value=fake_pool)):
        await arq_mod.init_pool()

    assert arq_mod._pool is fake_pool
    arq_mod._pool = None


@pytest.mark.asyncio
async def test_arq_close_pool_closes_and_clears():
    import app.arq_pool as arq_mod

    fake_pool = AsyncMock()
    arq_mod._pool = fake_pool

    await arq_mod.close_pool()

    fake_pool.close.assert_called_once()
    assert arq_mod._pool is None


@pytest.mark.asyncio
async def test_arq_close_pool_noop_when_none():
    import app.arq_pool as arq_mod

    arq_mod._pool = None
    await arq_mod.close_pool()  # must not raise


def test_arq_get_pool_returns_pool_when_initialized():
    import app.arq_pool as arq_mod

    fake_pool = MagicMock()
    arq_mod._pool = fake_pool

    result = arq_mod.get_pool()
    assert result is fake_pool
    arq_mod._pool = None


def test_arq_get_pool_raises_when_not_initialized():
    import app.arq_pool as arq_mod

    arq_mod._pool = None
    with pytest.raises(RuntimeError, match="not initialized"):
        arq_mod.get_pool()
