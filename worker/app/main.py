import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import asyncpg
from arq import create_pool as arq_create_pool
from arq.connections import RedisSettings

from .jobs import process_webhook
from .llm import build_provider
from .llm.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER

logger = logging.getLogger("worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            body = b'{"status":"ok","service":"worker"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def start_health_server() -> None:
    port = int(os.getenv("HEALTH_PORT", "8002"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info("health server listening on :%s", port)
    server.serve_forever()


async def startup(ctx: dict) -> None:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=2, max_size=10)
    ctx["db_pool"] = pool
    logger.info("worker db pool ready")

    arq_redis = await arq_create_pool(RedisSettings.from_dsn(redis_url))
    ctx["redis"] = arq_redis
    logger.info("arq pool ready")

    provider = build_provider(
        LLM_PROVIDER,
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
    )
    ctx["llm"] = provider
    logger.info("LLM provider ready: provider=%s model=%s", LLM_PROVIDER, LLM_MODEL)


async def shutdown(ctx: dict) -> None:
    arq_redis = ctx.get("redis")
    if arq_redis:
        await arq_redis.close()
    pool: asyncpg.Pool = ctx.get("db_pool")
    if pool:
        await pool.close()


class WorkerSettings:
    redis_settings = None  # populated at __main__ time from REDIS_URL
    functions = [process_webhook]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    max_tries = 3
    job_timeout = 300
    keep_result = 60


if __name__ == "__main__":
    import arq

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    logger.info("vellic worker starting, redis=%s", redis_url)
    WorkerSettings.redis_settings = RedisSettings.from_dsn(redis_url)

    thread = threading.Thread(target=start_health_server, daemon=True)
    thread.start()
    arq.run_worker(WorkerSettings)
