"""Unit tests for webhook retry logic and dead-letter queue."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq import Retry

from app.metrics import compute_retry_delays


# ---------------------------------------------------------------------------
# compute_retry_delays
# ---------------------------------------------------------------------------


def test_compute_retry_delays_defaults():
    delays = compute_retry_delays(max_retries=3, base_delay=5)
    assert delays == [5, 25, 125]


def test_compute_retry_delays_custom():
    delays = compute_retry_delays(max_retries=2, base_delay=10)
    assert delays == [10, 50]


def test_compute_retry_delays_single():
    delays = compute_retry_delays(max_retries=1, base_delay=30)
    assert delays == [30]


# ---------------------------------------------------------------------------
# _dead_letter — inserts into webhook_dlq
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dead_letter_inserts_dlq():
    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    job_id = uuid.uuid4()
    delivery_id = "test-delivery-1"
    payload = {"action": "opened"}
    exc = RuntimeError("pipeline exploded")

    with patch("app.jobs.webhook_dlq_depth") as mock_depth:
        from app.jobs import _dead_letter

        await _dead_letter(mock_pool, job_id, delivery_id, payload, exc, retry_count=3)

    # pipeline_jobs update, pipeline_failures insert, webhook_dlq upsert = 3 execute calls
    assert mock_conn.execute.call_count == 3

    # Verify the DLQ upsert was called with correct delivery_id
    dlq_call_args = mock_conn.execute.call_args_list[2]
    assert delivery_id in dlq_call_args[0]

    mock_depth.inc.assert_called_once()


# ---------------------------------------------------------------------------
# process_webhook retry flow
# ---------------------------------------------------------------------------

_PULL_REQUEST_ROW = {
    "event_type": "pull_request",
    "payload": {
        "repository": {"full_name": "a/b"},
        "pull_request": {
            "number": 1,
            "head": {"sha": "x"},
            "base": {"sha": "y", "ref": "main"},
            "title": "t",
            "body": "",
            "diff_url": "https://example.com",
        },
    },
}


def _make_ctx(job_try: int) -> dict:
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=_PULL_REQUEST_ROW)
    pool.fetch = AsyncMock(return_value=[])
    pool.execute = AsyncMock()
    return {"db_pool": pool, "redis": AsyncMock(), "job_try": job_try}


@pytest.mark.asyncio
async def test_process_webhook_retries_on_failure():
    """First attempt should raise Retry with exponential backoff delay."""
    ctx = _make_ctx(1)

    with (
        patch("app.jobs.get_max_retries", return_value=3),
        patch("app.jobs.get_retry_base_delay", return_value=5),
        patch("app.jobs.load_llm_config_from_db", new=AsyncMock(return_value=None)),
        patch(
            "app.jobs.load_env_llm_config",
            return_value={
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "api_key": "k",
                "base_url": "",
            },
        ),
        patch("app.jobs.build_provider"),
        patch("app.jobs.run_pipeline", new=AsyncMock(side_effect=RuntimeError("transient"))),
        patch("app.jobs._get_or_create_job", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.jobs.webhook_retry_total") as mock_counter,
    ):
        from app.jobs import process_webhook

        with pytest.raises(Retry) as exc_info:
            await process_webhook(ctx, "delivery-retry-1")

    # First retry delay: base_delay * 5^0 = 5s (defer_score is in ms)
    assert exc_info.value.defer_score == 5000
    mock_counter.inc.assert_called_once()


@pytest.mark.asyncio
async def test_process_webhook_dead_letters_on_max_attempts():
    """Final attempt should call _dead_letter and re-raise."""
    ctx = _make_ctx(4)  # job_try=4 = max_attempts for max_retries=3

    with (
        patch("app.jobs.get_max_retries", return_value=3),
        patch("app.jobs.get_retry_base_delay", return_value=5),
        patch("app.jobs.load_llm_config_from_db", new=AsyncMock(return_value=None)),
        patch(
            "app.jobs.load_env_llm_config",
            return_value={
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "api_key": "k",
                "base_url": "",
            },
        ),
        patch("app.jobs.build_provider"),
        patch("app.jobs.run_pipeline", new=AsyncMock(side_effect=RuntimeError("terminal"))),
        patch("app.jobs._get_or_create_job", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.jobs._dead_letter", new=AsyncMock()) as mock_dl,
        patch("app.jobs.webhook_retry_total"),
    ):
        from app.jobs import process_webhook

        with pytest.raises(RuntimeError, match="terminal"):
            await process_webhook(ctx, "delivery-final-1")

    mock_dl.assert_called_once()


@pytest.mark.asyncio
async def test_process_webhook_second_retry_uses_longer_delay():
    """Second retry (job_try=2) should use delay[1] = 25s."""
    ctx = _make_ctx(2)

    with (
        patch("app.jobs.get_max_retries", return_value=3),
        patch("app.jobs.get_retry_base_delay", return_value=5),
        patch("app.jobs.load_llm_config_from_db", new=AsyncMock(return_value=None)),
        patch(
            "app.jobs.load_env_llm_config",
            return_value={
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "api_key": "k",
                "base_url": "",
            },
        ),
        patch("app.jobs.build_provider"),
        patch("app.jobs.run_pipeline", new=AsyncMock(side_effect=RuntimeError("transient"))),
        patch("app.jobs._get_or_create_job", new=AsyncMock(return_value=uuid.uuid4())),
        patch("app.jobs.webhook_retry_total"),
    ):
        from app.jobs import process_webhook

        with pytest.raises(Retry) as exc_info:
            await process_webhook(ctx, "delivery-retry-2")

    assert exc_info.value.defer_score == 25000
