"""add prompt_overrides table

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-21

"""

from alembic import op

revision: str = "0011"
down_revision: str = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS prompt_overrides (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            repo_id     TEXT        NOT NULL,
            path        TEXT        NOT NULL,
            body        TEXT        NOT NULL,
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (repo_id, path)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_prompt_overrides_repo_id ON prompt_overrides (repo_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS prompt_overrides")
