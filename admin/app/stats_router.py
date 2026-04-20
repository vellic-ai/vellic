import logging

from fastapi import APIRouter

from . import db

logger = logging.getLogger("admin.stats")

router = APIRouter()

_STATS_SQL = """
WITH
  pr_24h AS (
    SELECT COUNT(*) AS cnt FROM pr_reviews
    WHERE posted_at >= NOW() - INTERVAL '24 hours'
  ),
  pr_7d AS (
    SELECT COUNT(*) AS cnt FROM pr_reviews
    WHERE posted_at >= NOW() - INTERVAL '7 days'
  ),
  latency AS (
    SELECT
      COALESCE(
        PERCENTILE_CONT(0.50) WITHIN GROUP (
          ORDER BY EXTRACT(EPOCH FROM (updated_at - created_at)) * 1000
        ), 0
      )::bigint AS p50_ms,
      COALESCE(
        PERCENTILE_CONT(0.95) WITHIN GROUP (
          ORDER BY EXTRACT(EPOCH FROM (updated_at - created_at)) * 1000
        ), 0
      )::bigint AS p95_ms
    FROM pipeline_jobs
    WHERE status = 'done'
      AND created_at >= NOW() - INTERVAL '7 days'
  ),
  fail AS (
    SELECT
      COUNT(*) FILTER (WHERE status = 'failed') AS failed,
      COUNT(*) FILTER (WHERE status IN ('done', 'failed')) AS total
    FROM pipeline_jobs
    WHERE created_at >= NOW() - INTERVAL '7 days'
  ),
  llm AS (
    SELECT provider, model FROM llm_settings WHERE id = 1
  )
SELECT
  (SELECT cnt FROM pr_24h)::int               AS prs_reviewed_24h,
  (SELECT cnt FROM pr_7d)::int                AS prs_reviewed_7d,
  (SELECT p50_ms FROM latency)                AS latency_p50_ms,
  (SELECT p95_ms FROM latency)                AS latency_p95_ms,
  CASE
    WHEN (SELECT total FROM fail) = 0 THEN 0.0
    ELSE ROUND(
      (SELECT failed FROM fail)::numeric
      / (SELECT total FROM fail)::numeric * 100,
      2
    )
  END                                         AS failure_rate_pct,
  (SELECT provider FROM llm)                  AS llm_provider,
  (SELECT model   FROM llm)                   AS llm_model
"""

_RECENT_SQL = """
SELECT
  wd.delivery_id,
  wd.event_type,
  wd.payload->'repository'->>'full_name' AS repo,
  wd.received_at,
  COALESCE(
    (
      SELECT CASE pj.status
        WHEN 'running' THEN 'running'
        WHEN 'done'    THEN 'done'
        WHEN 'failed'  THEN 'failed'
        ELSE 'running'
      END
      FROM pipeline_jobs pj
      WHERE pj.delivery_id = wd.delivery_id
      ORDER BY pj.created_at DESC
      LIMIT 1
    ),
    'pending'
  ) AS status
FROM webhook_deliveries wd
ORDER BY wd.received_at DESC
LIMIT 5
"""


@router.get("/admin/stats")
async def get_stats() -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_STATS_SQL)
        deliveries = await conn.fetch(_RECENT_SQL)

    recent = [
        {
            "delivery_id": d["delivery_id"],
            "event_type": d["event_type"],
            "repo": d["repo"],
            "received_at": d["received_at"].isoformat() if d["received_at"] else None,
            "status": d["status"],
        }
        for d in deliveries
    ]

    return {
        "prs_reviewed_24h": row["prs_reviewed_24h"] or 0,
        "prs_reviewed_7d": row["prs_reviewed_7d"] or 0,
        "latency_p50_ms": row["latency_p50_ms"] or 0,
        "latency_p95_ms": row["latency_p95_ms"] or 0,
        "failure_rate_pct": float(row["failure_rate_pct"] or 0),
        "llm_provider": row["llm_provider"],
        "llm_model": row["llm_model"],
        "recent_deliveries": recent,
    }
