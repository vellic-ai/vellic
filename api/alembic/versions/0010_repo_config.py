"""add repo_config table

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-21

"""

from alembic import op

revision: str = "0010"
down_revision: str = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS repo_config (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            repo_id     TEXT        NOT NULL UNIQUE,
            rules_yaml  TEXT        NOT NULL DEFAULT '',
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_repo_config_repo_id ON repo_config (repo_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS repo_config")
