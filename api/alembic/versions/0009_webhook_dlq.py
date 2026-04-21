"""add webhook_dlq table

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-21

"""

from alembic import op

revision: str = "0009"
down_revision: str = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS webhook_dlq (
            id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            delivery_id         TEXT        NOT NULL UNIQUE,
            job_id              UUID        REFERENCES pipeline_jobs(id) ON DELETE SET NULL,
            payload             JSONB       NOT NULL DEFAULT '{}',
            last_error          TEXT,
            retry_count         INT         NOT NULL DEFAULT 0,
            status              TEXT        NOT NULL DEFAULT 'pending'
                                            CHECK (status IN ('pending', 'discarded', 'replayed')),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_attempted_at   TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_dlq_status ON webhook_dlq (status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS webhook_dlq")
