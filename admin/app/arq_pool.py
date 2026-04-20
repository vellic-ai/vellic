import logging
import os

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

logger = logging.getLogger("admin.arq")

_pool: ArqRedis | None = None


async def init_pool() -> None:
    global _pool
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")
    _pool = await create_pool(RedisSettings.from_dsn(redis_url))
    logger.info("admin arq pool ready")


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> ArqRedis:
    if _pool is None:
        raise RuntimeError("arq pool not initialized")
    return _pool
