"""add webhook_config table

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-20

"""

from alembic import op

revision: str = "0006"
down_revision: str = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS webhook_config (
            id                      INT         PRIMARY KEY DEFAULT 1,
            url                     TEXT,
            hmac                    TEXT,
            github_app_id           TEXT,
            github_installation_id  TEXT,
            github_private_key      TEXT,
            gitlab_token            TEXT,
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT singleton    CHECK (id = 1)
        )
    """)
    op.execute("INSERT INTO webhook_config (id) VALUES (1) ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS webhook_config")
