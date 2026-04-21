"""add mcp_servers table

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-21

"""

from alembic import op

revision: str = "0013"
down_revision: str = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            installation_id  UUID        NOT NULL REFERENCES installations(id) ON DELETE CASCADE,
            name             TEXT        NOT NULL,
            url              TEXT        NOT NULL,
            credentials_enc  TEXT,
            enabled          BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_mcp_server_name UNIQUE (installation_id, name)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_mcp_servers_installation_id
            ON mcp_servers (installation_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mcp_servers")
