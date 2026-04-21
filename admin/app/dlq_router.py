"""Admin endpoints for the webhook dead-letter queue."""

import logging

from fastapi import APIRouter, HTTPException

from . import arq_pool, db

logger = logging.getLogger("admin.dlq")

router = APIRouter()


@router.get("/admin/dlq")
async def list_dlq(
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    pool = db.get_pool()
    query = """
    SELECT
        d.id::text              AS id,
        d.delivery_id,
        d.job_id::text          AS job_id,
        d.last_error,
        d.retry_count,
        d.status,
        d.created_at,
        d.last_attempted_at,
        wd.payload->'repository'->>'full_name'      AS repo,
        (wd.payload->'pull_request'->>'number')      AS pr_number,
        COUNT(*) OVER()                              AS total_count
    FROM webhook_dlq d
    LEFT JOIN webhook_deliveries wd ON wd.delivery_id = d.delivery_id
    WHERE ($3::text = '' OR d.status = $3)
    ORDER BY d.created_at DESC
    LIMIT $1 OFFSET $2
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, limit, offset, status)

    total = rows[0]["total_count"] if rows else 0
    items = [
        {
            "id": r["id"],
            "delivery_id": r["delivery_id"],
            "job_id": r["job_id"],
            "last_error": r["last_error"],
            "retry_count": r["retry_count"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "last_attempted_at": r["last_attempted_at"].isoformat()
            if r["last_attempted_at"]
            else None,
            "repo": r["repo"],
            "pr_number": r["pr_number"],
        }
        for r in rows
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/admin/dlq/{dlq_id}/replay", status_code=202)
async def replay_dlq_entry(dlq_id: str) -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id::text, delivery_id, status FROM webhook_dlq WHERE id = $1::uuid",
            dlq_id,
        )

    if row is None:
        raise HTTPException(status_code=404, detail=f"DLQ entry {dlq_id!r} not found")
    if row["status"] == "discarded":
        raise HTTPException(
            status_code=409,
            detail="entry has been discarded and cannot be replayed",
        )

    arq = arq_pool.get_pool()
    await arq.enqueue_job("process_webhook", row["delivery_id"])

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE webhook_dlq SET status = 'replayed' WHERE id = $1::uuid",
            dlq_id,
        )

    logger.info("replayed dlq_id=%s delivery=%s", dlq_id, row["delivery_id"])
    return {"status": "queued", "delivery_id": row["delivery_id"]}


@router.delete("/admin/dlq/{dlq_id}")
async def discard_dlq_entry(dlq_id: str) -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id::text, delivery_id, status FROM webhook_dlq WHERE id = $1::uuid",
            dlq_id,
        )

    if row is None:
        raise HTTPException(status_code=404, detail=f"DLQ entry {dlq_id!r} not found")
    if row["status"] == "discarded":
        raise HTTPException(status_code=409, detail="entry is already discarded")

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE webhook_dlq SET status = 'discarded' WHERE id = $1::uuid",
            dlq_id,
        )

    logger.info("discarded dlq_id=%s delivery=%s", dlq_id, row["delivery_id"])
    return {"status": "discarded", "dlq_id": dlq_id}
