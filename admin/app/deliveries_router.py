import logging

from fastapi import APIRouter, HTTPException

from . import arq_pool, db

logger = logging.getLogger("admin.deliveries")

router = APIRouter()

_DELIVERIES_SQL = """
WITH ds AS (
    SELECT
        wd.delivery_id,
        wd.event_type,
        wd.received_at,
        wd.processed_at,
        COALESCE(
            (SELECT CASE pj.status
                WHEN 'running' THEN 'running'
                WHEN 'done'    THEN 'done'
                WHEN 'failed'  THEN 'failed'
                ELSE 'running'
             END
             FROM pipeline_jobs pj
             WHERE pj.delivery_id = wd.delivery_id
             ORDER BY pj.created_at DESC
             LIMIT 1),
            'pending'
        ) AS status,
        (SELECT id::text
         FROM pipeline_jobs
         WHERE delivery_id = wd.delivery_id
         ORDER BY created_at DESC
         LIMIT 1) AS job_id
    FROM webhook_deliveries wd
)
SELECT *, COUNT(*) OVER() AS total_count
FROM ds
WHERE ($3::text = '' OR status = $3)
  AND event_type ILIKE $4
ORDER BY received_at DESC
LIMIT $1 OFFSET $2
"""


@router.get("/admin/deliveries")
async def list_deliveries(
    limit: int = 50,
    offset: int = 0,
    status: str = "",
    event_type: str = "",
) -> dict:
    pool = db.get_pool()
    et_pattern = f"%{event_type}%" if event_type else "%"
    async with pool.acquire() as conn:
        rows = await conn.fetch(_DELIVERIES_SQL, limit, offset, status, et_pattern)

    row_total = rows[0]["total_count"] if rows else 0
    items = [
        {
            "delivery_id": r["delivery_id"],
            "event_type": r["event_type"],
            "received_at": r["received_at"].isoformat() if r["received_at"] else None,
            "processed_at": r["processed_at"].isoformat() if r["processed_at"] else None,
            "status": r["status"],
            "job_id": r["job_id"],
        }
        for r in rows
    ]
    return {"items": items, "total": row_total, "limit": limit, "offset": offset}


@router.post("/admin/replay/{delivery_id}", status_code=202)
async def replay_delivery(delivery_id: str) -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT delivery_id, event_type FROM webhook_deliveries WHERE delivery_id = $1",
            delivery_id,
        )

    if row is None:
        raise HTTPException(status_code=404, detail=f"delivery {delivery_id!r} not found")

    arq = arq_pool.get_pool()
    await arq.enqueue_job("process_webhook", delivery_id)
    logger.info("replayed delivery=%s event=%s", delivery_id, row["event_type"])

    return {"status": "queued", "delivery_id": delivery_id, "event_type": row["event_type"]}
