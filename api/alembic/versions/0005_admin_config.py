"""add admin_config table

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-20

"""

from alembic import op

revision: str = "0005"
down_revision: str = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS admin_config (
            key        TEXT        PRIMARY KEY,
            value      TEXT        NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS admin_config")
