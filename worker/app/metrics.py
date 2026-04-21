import os

from prometheus_client import Counter, Gauge

_NAMESPACE = "vellic"

webhook_retry_total = Counter(
    f"{_NAMESPACE}_webhook_retry_total",
    "Total number of webhook processing retry attempts",
)

webhook_dlq_depth = Gauge(
    f"{_NAMESPACE}_webhook_dlq_depth",
    "Current number of pending items in the dead-letter queue",
)


def get_max_retries() -> int:
    return int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))


def get_retry_base_delay() -> int:
    return int(os.getenv("WEBHOOK_RETRY_BASE_DELAY", "5"))


def compute_retry_delays(max_retries: int, base_delay: int) -> list[int]:
    """Return list of backoff delays (seconds) for retries 1..max_retries."""
    return [base_delay * (5**i) for i in range(max_retries)]
