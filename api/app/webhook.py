import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from .arq_pool import get_pool as get_arq_pool
from .db import get_pool as get_db_pool

logger = logging.getLogger("api.webhook")

router = APIRouter()

_PR_ACTIONS = {"opened", "synchronize", "reopened"}
_HANDLED_EVENTS = {"pull_request", "pull_request_review"}


def _verify_signature(body: bytes, sig_header: str) -> bool:
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        logger.error("GITHUB_WEBHOOK_SECRET not set — rejecting all webhooks")
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)


@router.post("/webhook/github")
async def github_webhook(request: Request) -> Response:
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    event_type = request.headers.get("X-GitHub-Event", "")
    sig_header = request.headers.get("X-Hub-Signature-256", "")

    body = await request.body()
    if not _verify_signature(body, sig_header):
        return Response(status_code=400)

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
            datetime.now(timezone.utc),
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
