import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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
        pass  # suppress default access log noise


def start_health_server() -> None:
    port = int(os.getenv("HEALTH_PORT", "8002"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info("health server listening on :%s", port)
    server.serve_forever()


# Arq worker settings — full job definitions added in Sprint 1
class WorkerSettings:
    redis_settings = None  # populated from env at startup
    functions: list = []
    max_jobs = 10
    job_timeout = 300
    keep_result = 60


if __name__ == "__main__":
    import arq

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    logger.info("vellic worker starting, redis=%s", redis_url)
    thread = threading.Thread(target=start_health_server, daemon=True)
    thread.start()
    arq.run_worker(WorkerSettings)
