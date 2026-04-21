"""Shared test fixtures for admin service tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app import db


@pytest.fixture(autouse=True)
def mock_db_pool(monkeypatch):
    """Stub the asyncpg pool so unit tests never need a real database."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr(db, "_pool", pool)
    return conn
