import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import arq_pool, db
from .auth_router import AdminAuthMiddleware
from .auth_router import router as auth_router
from .deliveries_router import router as deliveries_router
from .repos_router import router as repos_router
from .settings_router import router as settings_router
from .stats_router import router as stats_router

_STATIC = Path(__file__).parent.parent / "static"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("admin")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("vellic admin starting on port %s", os.getenv("PORT", "8001"))
    await db.init_pool()
    await arq_pool.init_pool()
    yield
    await arq_pool.close_pool()
    await db.close_pool()


app = FastAPI(title="vellic-admin", version="0.1.0", lifespan=lifespan)
app.add_middleware(AdminAuthMiddleware)
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(repos_router)
app.include_router(stats_router)
app.include_router(deliveries_router)

if _STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "admin"}


@app.get("/")
async def admin_root() -> FileResponse:
    return FileResponse(str(_STATIC / "index.html"))


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
async def admin_spa(path: str) -> FileResponse:
    return FileResponse(str(_STATIC / "index.html"))
