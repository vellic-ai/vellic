"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-20

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS webhook_deliveries (
            delivery_id  TEXT        PRIMARY KEY,
            event_type   TEXT        NOT NULL,
            payload      JSONB       NOT NULL,
            received_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            processed_at TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_jobs (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            delivery_id TEXT        NOT NULL REFERENCES webhook_deliveries(delivery_id),
            status      TEXT        NOT NULL DEFAULT 'queued',
            retry_count INT         NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_failures (
            id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            job_id    UUID        NOT NULL REFERENCES pipeline_jobs(id),
            payload   JSONB       NOT NULL,
            error     TEXT        NOT NULL,
            failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS pr_reviews (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            repo        TEXT        NOT NULL,
            pr_number   INT         NOT NULL,
            commit_sha  TEXT        NOT NULL,
            analysis_id TEXT,
            posted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_pr_reviews_repo_pr_sha UNIQUE (repo, pr_number, commit_sha)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS installations (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            platform    TEXT        NOT NULL,
            org         TEXT        NOT NULL,
            repo        TEXT,
            config_json JSONB       NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_delivery_id
            ON pipeline_jobs (delivery_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_status
            ON pipeline_jobs (status)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_pipeline_failures_job_id
            ON pipeline_failures (job_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pipeline_failures")
    op.execute("DROP TABLE IF EXISTS pipeline_jobs")
    op.execute("DROP TABLE IF EXISTS pr_reviews")
    op.execute("DROP TABLE IF EXISTS installations")
    op.execute("DROP TABLE IF EXISTS webhook_deliveries")
