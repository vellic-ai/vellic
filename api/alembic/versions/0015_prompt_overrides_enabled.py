"""add enabled column to prompt_overrides (VEL-134)

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-21

"""

from alembic import op

revision: str = "0015"
down_revision: str = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE prompt_overrides
        ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE prompt_overrides DROP COLUMN IF EXISTS enabled")
