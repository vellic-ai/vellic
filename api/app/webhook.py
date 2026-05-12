import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

import asyncpg
from fastapi import APIRouter, HTTPException, Request, Response
from vellic_crypto import decrypt

from .arq_pool import get_pool as get_arq_pool
from .db import get_pool as get_db_pool
from .rate_limit import check_rate_limit

logger = logging.getLogger("api.webhook")

router = APIRouter()

_PR_ACTIONS = {"opened", "synchronize", "reopened"}
_HANDLED_EVENTS = {"pull_request", "pull_request_review"}


# ---------------------------------------------------------------------------
# Shared HMAC secret (webhook_config.hmac) — used by all VCS adapters.
# ---------------------------------------------------------------------------


async def _load_webhook_secret() -> str | None:
    """Return the decrypted webhook HMAC secret from the DB, or None if unset."""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow("SELECT hmac FROM webhook_config WHERE id = 1")
        except asyncpg.exceptions.UndefinedTableError:
            # Pre-migration — treat as unconfigured so all webhooks are rejected.
            return None
    if not row or not row["hmac"]:
        return None
    try:
        return decrypt(row["hmac"])
    except Exception as exc:
        logger.error("failed to decrypt webhook_config.hmac: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def _verify_hmac_signature(body: bytes, sig_header: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)


async def _verify_github_signature(body: bytes, sig_header: str) -> bool:
    secret = await _load_webhook_secret()
    if not secret:
        logger.error("webhook_config.hmac not configured — rejecting all webhooks")
        return False
    return _verify_hmac_signature(body, sig_header, secret)


async def _verify_gitlab_signature(token_header: str) -> bool:
    """GitLab sends X-Gitlab-Token as a plain shared secret (no HMAC)."""
    secret = await _load_webhook_secret()
    if not secret:
        logger.error("webhook_config.hmac not configured — rejecting all webhooks")
        return False
    return hmac.compare_digest(secret, token_header)


async def _verify_bitbucket_signature(body: bytes, sig_header: str) -> bool:
    """Bitbucket Cloud sends X-Hub-Signature: sha256=<hex>."""
    secret = await _load_webhook_secret()
    if not secret:
        logger.error("webhook_config.hmac not configured — rejecting all webhooks")
        return False
    return _verify_hmac_signature(body, sig_header, secret)


# ---------------------------------------------------------------------------
# Shared DB / queue helper
# ---------------------------------------------------------------------------


async def _persist_and_enqueue(delivery_id: str, event_type: str, payload: dict) -> Response:
    db = get_db_pool()
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO webhook_deliveries (delivery_id, event_type, payload, received_at)
            VALUES ($1, $2, $3::jsonb, $4)
            ON CONFLICT (delivery_id) DO NOTHING
            RETURNING delivery_id
            """,
            delivery_id,
            event_type,
            json.dumps(payload),
            datetime.now(UTC),
        )

    if row is None:
        logger.info("duplicate delivery %s — skipping", delivery_id)
        return Response(
            status_code=200,
            content=json.dumps({"status": "duplicate", "delivery_id": delivery_id}),
            media_type="application/json",
        )

    arq = get_arq_pool()
    await arq.enqueue_job("process_webhook", delivery_id)
    logger.info("enqueued %s event delivery=%s", event_type, delivery_id)

    return Response(
        status_code=202,
        content=json.dumps({"status": "accepted", "delivery_id": delivery_id}),
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


@router.post("/webhook/github")
async def github_webhook(request: Request) -> Response:
    blocked = await check_rate_limit(request)
    if blocked is not None:
        return blocked

    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    event_type = request.headers.get("X-GitHub-Event", "")
    sig_header = request.headers.get("X-Hub-Signature-256", "")

    body = await request.body()
    if not await _verify_github_signature(body, sig_header):
        return Response(status_code=401)

    if not delivery_id:
        raise HTTPException(status_code=400, detail="missing X-GitHub-Delivery header")

    if event_type not in _HANDLED_EVENTS:
        return Response(
            status_code=200,
            content=json.dumps({"status": "ignored", "event": event_type}),
            media_type="application/json",
        )

    payload = json.loads(body)

    if event_type == "pull_request" and payload.get("action") not in _PR_ACTIONS:
        return Response(
            status_code=200,
            content=json.dumps({"status": "ignored", "action": payload.get("action")}),
            media_type="application/json",
        )

    return await _persist_and_enqueue(delivery_id, event_type, payload)


# ---------------------------------------------------------------------------
# GitLab
# ---------------------------------------------------------------------------

_GITLAB_HANDLED_EVENTS = {"Merge Request Hook", "Note Hook"}
_MR_ACTIONS = {"open", "reopen", "update"}


@router.post("/webhook/gitlab")
async def gitlab_webhook(request: Request) -> Response:
    blocked = await check_rate_limit(request)
    if blocked is not None:
        return blocked

    event_type = request.headers.get("X-Gitlab-Event", "")
    token_header = request.headers.get("X-Gitlab-Token", "")

    body = await request.body()
    if not await _verify_gitlab_signature(token_header):
        return Response(status_code=401)

    payload = json.loads(body)
    obj_attrs = payload.get("object_attributes", {})
    obj_id = str(obj_attrs.get("id", ""))
    received_ts = datetime.now(UTC).isoformat()
    delivery_id = f"gitlab-{obj_id}-{received_ts}" if obj_id else f"gitlab-{received_ts}"

    if event_type not in _GITLAB_HANDLED_EVENTS:
        return Response(
            status_code=200,
            content=json.dumps({"status": "ignored", "event": event_type}),
            media_type="application/json",
        )

    if event_type == "Merge Request Hook":
        action = obj_attrs.get("action", "")
        if action not in _MR_ACTIONS:
            return Response(
                status_code=200,
                content=json.dumps({"status": "ignored", "action": action}),
                media_type="application/json",
            )

    return await _persist_and_enqueue(delivery_id, event_type, payload)


# ---------------------------------------------------------------------------
# Bitbucket
# ---------------------------------------------------------------------------

_BITBUCKET_HANDLED_EVENTS = {
    "pullrequest:created",
    "pullrequest:updated",
    "pullrequest:fulfilled",
}


@router.post("/webhook/bitbucket")
async def bitbucket_webhook(request: Request) -> Response:
    blocked = await check_rate_limit(request)
    if blocked is not None:
        return blocked

    event_type = request.headers.get("X-Event-Key", "")
    sig_header = request.headers.get("X-Hub-Signature", "")
    delivery_id = request.headers.get("X-Request-UUID", "")

    body = await request.body()
    if not await _verify_bitbucket_signature(body, sig_header):
        return Response(status_code=401)

    if not delivery_id:
        delivery_id = f"bb-{datetime.now(UTC).isoformat()}"

    if event_type not in _BITBUCKET_HANDLED_EVENTS:
        return Response(
            status_code=200,
            content=json.dumps({"status": "ignored", "event": event_type}),
            media_type="application/json",
        )

    payload = json.loads(body)
    return await _persist_and_enqueue(delivery_id, event_type, payload)
