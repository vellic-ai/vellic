import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import arq_pool, db
from .auth_router import AdminAuthMiddleware
from .auth_router import router as auth_router
from .dlq_router import router as dlq_router
from .features_router import router as features_router
from .repos_router import router as repos_router
from .settings_router import router as settings_router
from .stats_router import router as stats_router

_STATIC = Path(__file__).parent.parent / "static"

# VELLIC_ADMIN_V2=1 means the nginx frontend serves the SPA; admin/static/ is deprecated.
# Set to 0 (default) until VEL-51 e2e green run confirms SPA stability.
_ADMIN_V2 = os.getenv("VELLIC_ADMIN_V2", "0") == "1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("admin")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("vellic admin starting on port %s (v2=%s)", os.getenv("PORT", "8001"), _ADMIN_V2)
    if _ADMIN_V2:
        # @deprecated: admin/static/ is superseded by the nginx SPA bundle (VEL-52).
        # Scheduled for removal after 7 days of stable staging; track in VEL-52 deprecation plan.
        logger.warning(
            "VELLIC_ADMIN_V2=1: admin/static/ serving is deprecated — SPA served by nginx"
        )
    await db.init_pool()
    await arq_pool.init_pool()
    yield
    await arq_pool.close_pool()
    await db.close_pool()


app = FastAPI(title="vellic-admin", version="0.1.0", lifespan=lifespan)
app.add_middleware(AdminAuthMiddleware)
app.include_router(auth_router)
app.include_router(features_router)
app.include_router(settings_router)
app.include_router(repos_router)
app.include_router(stats_router)
app.include_router(dlq_router)

# @deprecated (VELLIC_ADMIN_V2): static mount removed when flag=1; nginx handles SPA routing.
if not _ADMIN_V2 and _STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "admin"}


@app.get("/")
async def admin_root() -> Response:
    # @deprecated (VELLIC_ADMIN_V2): when flag=1, nginx serves / directly from SPA dist.
    if _ADMIN_V2:
        return Response(status_code=404, content="served by nginx")
    return FileResponse(str(_STATIC / "index.html"))


@app.get("/admin/deliveries")
async def list_deliveries(
    limit: int = 50,
    offset: int = 0,
    status: str = "",
    event_type: str = "",
) -> dict:
    pool = db.get_pool()
    et_pattern = f"%{event_type}%" if event_type else "%"

    query = """
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

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, limit, offset, status, et_pattern)

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


@app.get("/admin/jobs")
async def list_jobs(
    limit: int = 50,
    offset: int = 0,
    status: str = "",
) -> dict:
    pool = db.get_pool()
    query = """
    WITH js AS (
        SELECT
            pj.id::text                                                     AS id,
            pj.delivery_id,
            pj.status,
            pj.retry_count,
            pj.created_at,
            ROUND(EXTRACT(EPOCH FROM (pj.updated_at - pj.created_at)) * 1000)::bigint
                                                                            AS duration_ms,
            wd.payload->'repository'->>'full_name'                          AS repo,
            (wd.payload->'pull_request'->>'number')::text                   AS pr_number,
            (SELECT pf.error
             FROM pipeline_failures pf
             WHERE pf.job_id = pj.id
             ORDER BY pf.failed_at DESC
             LIMIT 1)                                                        AS error
        FROM pipeline_jobs pj
        JOIN webhook_deliveries wd ON wd.delivery_id = pj.delivery_id
        WHERE ($3::text = '' OR pj.status = $3)
    )
    SELECT *, COUNT(*) OVER() AS total_count
    FROM js
    ORDER BY created_at DESC
    LIMIT $1 OFFSET $2
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, limit, offset, status)

    row_total = rows[0]["total_count"] if rows else 0
    items = [
        {
            "id": r["id"],
            "delivery_id": r["delivery_id"],
            "status": r["status"],
            "retry_count": r["retry_count"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "duration_ms": r["duration_ms"],
            "repo": r["repo"],
            "pr_number": r["pr_number"],
            "platform": "github",
            "error": r["error"],
        }
        for r in rows
    ]
    return {"items": items, "total": row_total, "limit": limit, "offset": offset}


@app.get("/{path:path}")
async def admin_spa(path: str) -> Response:
    if _ADMIN_V2:
        return Response(status_code=404, content="served by nginx")
    return FileResponse(str(_STATIC / "index.html"))


@app.post("/admin/replay/{delivery_id}", status_code=202)
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
