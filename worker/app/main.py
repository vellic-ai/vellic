import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import asyncpg
from arq import create_pool as arq_create_pool
from arq.connections import RedisSettings
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .jobs import post_feedback, process_webhook
from .mcp_host import get_manager as get_mcp_manager
from .metrics import get_max_retries, webhook_dlq_depth

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
        elif self.path == "/metrics":
            output = generate_latest()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(output)))
            self.end_headers()
            self.wfile.write(output)
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

    # Initialise dlq_depth gauge from DB so it survives restarts
    try:
        count = await pool.fetchval(
            "SELECT COUNT(*) FROM webhook_dlq WHERE status = 'pending'"
        )
        webhook_dlq_depth.set(count or 0)
        logger.info("dlq_depth initialised to %d", count or 0)
    except Exception:
        logger.warning("could not initialise dlq_depth gauge (table may not exist yet)")

    logger.info("LLM config will be loaded from DB per job (env vars as fallback)")

    mcp_manager = get_mcp_manager()
    await mcp_manager.start()
    ctx["mcp_manager"] = mcp_manager
    logger.info("mcp process manager started")


async def shutdown(ctx: dict) -> None:
    mcp_manager = ctx.get("mcp_manager")
    if mcp_manager:
        await mcp_manager.stop()
    arq_redis = ctx.get("redis")
    if arq_redis:
        await arq_redis.close()
    pool: asyncpg.Pool = ctx.get("db_pool")
    if pool:
        await pool.close()


class WorkerSettings:
    redis_settings = None  # populated at __main__ time from REDIS_URL
    functions = [process_webhook, post_feedback]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    max_tries = get_max_retries() + 1  # initial attempt + max_retries retries
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
